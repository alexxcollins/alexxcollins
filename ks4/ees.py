"""Minimal client for the DfE Explore Education Statistics (EES) public API."""
import time

import numpy as np
import pandas as pd
import requests

BASE = "https://api.education.gov.uk/statistics/v1"

# DfE suppression / special codes -> NaN (never 0). The second group are the
# codes used in the legacy performance-tables CSV downloads.
SUPPRESSION_CODES = {"z", "c", "x", "low", "u", "k", ":", "",
                     "supp", "ne", "np", "na", "lowcov", "new", "dns"}


def get(path, **params):
    r = requests.get(f"{BASE}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def meta(data_set_id):
    return get(f"/data-sets/{data_set_id}/meta")


def to_num(s):
    """Coerce a series of strings to float, mapping DfE suppression codes to NaN."""
    s = s.astype("string").str.strip()
    s = s.mask(s.str.lower().isin(SUPPRESSION_CODES))
    return pd.to_numeric(s, errors="coerce").astype(float)


def query(data_set_id, criteria, indicators, page_size=1000):
    """POST /data-sets/{id}/query, following pagination. Returns raw result rows."""
    rows, page = [], 1
    while True:
        body = {"criteria": criteria, "indicators": indicators,
                "page": page, "pageSize": page_size}
        for attempt in range(4):
            r = requests.post(
                f"{BASE}/data-sets/{data_set_id}/query",
                json=body,
                timeout=120,
            )
            if r.status_code < 500:
                break
            time.sleep(2 ** (attempt + 1))
        r.raise_for_status()
        d = r.json()
        rows.extend(d["results"])
        if page >= d["paging"]["totalPages"]:
            return rows, d.get("warnings")
        page += 1


def results_to_frame(rows, meta_json):
    """Flatten API results into a tidy frame with human-readable column names."""
    filt_col = {}
    opt_label = {}
    for f in meta_json["filters"]:
        for o in f["options"]:
            filt_col[o["id"]] = f["column"]
            opt_label[o["id"]] = o["label"]
    ind_col = {i["id"]: i["column"] for i in meta_json["indicators"]}
    loc = {}
    for lvl in meta_json["locations"]:
        for o in lvl["options"]:
            loc[o["id"]] = o

    out = []
    for r in rows:
        rec = {"time_period": r["timePeriod"]["period"]}
        for lvl, lid in r["locations"].items():
            o = loc.get(lid, {})
            if lvl == "SCH":
                rec["urn"] = o.get("urn")
                rec["school_name_api"] = o.get("label")
            elif lvl == "LA":
                rec["la_name"] = o.get("label")
                rec["old_la_code"] = o.get("oldCode")
        for fid, oid in r["filters"].items():
            rec[filt_col.get(oid, fid)] = opt_label.get(oid, oid)
        for iid, v in r["values"].items():
            rec[ind_col.get(iid, iid)] = v
        out.append(rec)
    df = pd.DataFrame(out)
    for c in ind_col.values():
        if c in df:
            df[c] = to_num(df[c])
    return df
