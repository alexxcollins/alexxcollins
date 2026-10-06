"""Pull DfE KS4 institution-level data from the EES public API and build outputs.

Usage:
    python ks4/fetch_ks4.py discover   # find 2024/25 data set IDs, save meta JSON
    python ks4/fetch_ks4.py output1    # high-prior-attainer P8, 2023/24

Downloads land in ks4/raw/, outputs in ks4/out/.
"""

import io
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API = "https://api.education.gov.uk/statistics/v1"
CATALOGUE_CSV = "https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/{id}/csv"

HERE = Path(__file__).parent
RAW = HERE / "raw"
OUT = HERE / "out"

DATA_SETS = {
    "perf_2324": "c8f753ef-b76f-41a3-8949-13382e131054",
    "info_2324": "d7ce19cb-916b-45d6-9dc1-3e581e16fa1a",
    # perf_2425 / info_2425 are filled in by `discover` (saved to raw/data_set_ids.json)
}

SCHOOLS = {
    "131609": "The Bridge Academy",
    "134693": "Mossbourne Community Academy",
    "140210": "Mossbourne Victoria Park Academy",
    "135835": "The City Academy, Hackney",
    "143756": "City of London Academy Shoreditch Park",
    "137442": "Clapton Girls' Academy",
    "131062": "The Excelsior Academy",
    "100279": "Stoke Newington School",
    "147653": "Waterside Academy",
    "134314": "St Mary Magdalene Academy",
    "102055": "The Latymer School",
}
# Looked up by name because the URN changed on academy conversion.
SCHOOLS_BY_NAME = ["Haggerston School"]

SUPPRESSION = ["z", "c", "x", "low", "u", "k", ":", ""]

session = requests.Session()
session.headers["Accept"] = "application/json"


def get(path, **params):
    r = session.get(f"{API}{path}", params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def save_json(obj, name):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_text(json.dumps(obj, indent=2))


# ---------------------------------------------------------------- discovery

def discover():
    for key, ds_id in DATA_SETS.items():
        meta = get(f"/data-sets/{ds_id}/meta")
        save_json(meta, f"meta_{key}.json")
        print(f"{key}: {len(meta.get('filters', []))} filters, "
              f"{len(meta.get('indicators', []))} indicators")

    pubs = get("/publications", search="key stage 4", pageSize=40)["results"]
    found = {}
    for pub in pubs:
        sets = get(f"/publications/{pub['id']}/data-sets", pageSize=40)["results"]
        for ds in sets:
            title = ds["title"]
            print(f"  [{pub['title']}] {title}  ->  {ds['id']}")
            if re.search(r"institution level 2025", title, re.I):
                kind = "info" if re.search(r"information", title, re.I) else "perf"
                found[f"{kind}_2425"] = ds["id"]
    save_json(found, "data_set_ids.json")
    print("2024/25 data sets found:", found or "none (fall back to catalogue download)")
    for key, ds_id in found.items():
        save_json(get(f"/data-sets/{ds_id}/meta"), f"meta_{key}.json")


def all_ids():
    ids = dict(DATA_SETS)
    f = RAW / "data_set_ids.json"
    if f.exists():
        ids.update(json.loads(f.read_text()))
    return ids


# ---------------------------------------------------------------- download

def download_csv(key):
    """Full data set CSV via the API, falling back to the data catalogue."""
    dest = RAW / f"{key}.csv"
    if dest.exists():
        return dest
    ds_id = all_ids()[key]
    RAW.mkdir(parents=True, exist_ok=True)
    for url in (f"{API}/data-sets/{ds_id}/csv", CATALOGUE_CSV.format(id=ds_id)):
        r = session.get(url, timeout=600, headers={"Accept": "text/csv, application/zip, */*"})
        if r.ok:
            break
        print(f"  {url} -> {r.status_code}")
    else:
        raise RuntimeError(f"Could not download {key} ({ds_id})")
    content = r.content
    if content[:2] == b"PK":  # zipped
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            name = max((n for n in z.namelist() if n.endswith(".csv")),
                       key=lambda n: z.getinfo(n).file_size)
            content = z.read(name)
    dest.write_bytes(content)
    return dest


def load(key):
    return pd.read_csv(download_csv(key), dtype=str, na_values=SUPPRESSION,
                       keep_default_na=False, low_memory=False)


def to_num(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")  # suppression already NaN
    return df


# ---------------------------------------------------------------- output 1

def find_col(df, *patterns):
    for p in patterns:
        hits = [c for c in df.columns if re.fullmatch(p, c, re.I)]
        if hits:
            return hits[0]
    raise KeyError(f"No column matching {patterns}; have {list(df.columns)}")


def output1():
    perf = load("perf_2324")
    urn = find_col(perf, "school_urn", "urn")
    name = find_col(perf, "school_name", "name")

    haggerston = perf.loc[perf[name].str.contains("Haggerston", case=False, na=False), [urn, name]]
    print("Haggerston matches:\n", haggerston.drop_duplicates().to_string(index=False))
    urns = set(SCHOOLS) | set(haggerston[urn])

    # The prior-attainment breakdown is either its own column or a
    # breakdown_topic/breakdown pair, depending on how DfE shaped the file.
    sub = perf[perf[urn].isin(urns)].copy()
    if "prior_attainment" in sub.columns:
        pa = sub["prior_attainment"]
        others = [c for c in ("sex", "disadvantage", "disadvantage_status", "ethnicity_major",
                              "first_language", "sen_status") if c in sub.columns]
        mask = pa.str.fullmatch(r"(?i)high.*", na=False)
        for c in others:
            mask &= sub[c].str.fullmatch(r"(?i)total|all.*", na=False)
    else:
        topic = find_col(sub, "breakdown_topic")
        bd = find_col(sub, "breakdown")
        mask = (sub[topic].str.contains("prior attainment", case=False, na=False)
                & sub[bd].str.fullmatch(r"(?i)high.*", na=False))
    sub = sub[mask]

    cols = ["avg_p8score", "p8score_ci_low", "p8score_ci_upp", "t_inp8calc", "avg_att8", "t_pupils"]
    sub = to_num(sub, cols)
    out = sub[[urn, name] + cols].rename(columns={urn: "urn", name: "school_name"})
    out = out.sort_values("avg_p8score", ascending=False)

    missing = urns - set(out["urn"])
    if missing:
        print("No high-prior-attainer row for URNs:", sorted(missing))
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "output1_high_pa_p8_2023_24.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    {"discover": discover, "output1": output1}[sys.argv[1]]()
