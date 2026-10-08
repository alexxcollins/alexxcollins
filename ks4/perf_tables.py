"""Loader for the legacy school performance tables KS4 CSV downloads.

School-level KS4 data before 2022/23 is not on Explore Education Statistics;
it is only on the performance tables service ("Compare school and college
performance"). Its Azure front door rejects non-browser user agents, hence
the explicit User-Agent header.
"""
import time
from pathlib import Path

import pandas as pd
import requests

import ees

URL = ("https://www.compare-school-performance.service.gov.uk/download-data"
       "?download=true&regions=0&filters=KS4&fileformat=csv&year={year}&meta=false")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
CACHE = Path(__file__).parent / "data" / "raw"

# High-prior-attainment KS4 columns -> tidy names (match the EES-derived frame)
HPA_COLUMNS = {
    "P8MEA_HI": "p8_avg",
    "P8CILOW_HI": "p8_ci_low",
    "P8CIUPP_HI": "p8_ci_upp",
    "P8PUP_HI": "n_in_p8",
    "ATT8SCR_HI": "a8_avg",
    "TPRIORHI": "n_pupils",
}


def download(year):
    """year like '2018-2019'. Cached under data/raw."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"ks4_{year}.csv"
    if not path.exists():
        for attempt in range(4):  # the front door occasionally returns a transient 403
            r = requests.get(URL.format(year=year), headers={"User-Agent": UA}, timeout=300)
            if r.status_code != 403:
                break
            time.sleep(2 ** (attempt + 1))
        r.raise_for_status()
        if "csv" not in r.headers.get("content-type", ""):
            raise RuntimeError(f"Unexpected content type for {year}: {r.headers.get('content-type')}")
        path.write_bytes(r.content)
    return path


def high_pa(year, urns):
    """High-prior-attainment P8/A8 rows for the given URNs from one year's file."""
    df = pd.read_csv(download(year), dtype=str, encoding="utf-8-sig",
                     usecols=["URN", "SCHNAME", *HPA_COLUMNS])
    df = df[df.URN.isin(urns)].rename(columns={"URN": "urn", "SCHNAME": "school_name_source"})
    df = df.rename(columns=HPA_COLUMNS)
    for c in HPA_COLUMNS.values():
        df[c] = ees.to_num(df[c])
    df["time_period"] = year.replace("-20", "/")  # 2018-2019 -> 2018/19
    df["source"] = "performance tables CSV"
    return df
