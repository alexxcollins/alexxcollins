"""KS4 league tables by Attainment 8, 2024/25 (final), state-funded mainstream schools.

Source: england_ks4final.csv for 2024-2025 from the school performance tables
download service (compare-school-performance.service.gov.uk). Local authority
names come from the EES API location list, matched on the LEA code.

Filters:
  - RECTYPE == 1 (mainstream schools; special schools are RECTYPE 2)
  - NFTYPE in STATE_MAINSTREAM (drops IND independent and FESI FE colleges)
  - TPUP (pupils at end of KS4) >= 30
  - ATT8SCR numeric (SUPP / NE / missing dropped)
  - Gender from EGENDER (KS4 gender), selective = ADMPOL == "SEL"
Progress 8 was not calculated for 2024/25 (no KS2 tests in 2020), so P8 is empty.
"""
import pandas as pd

import ees
import perf_tables
from output1_high_pa_p8_2024 import DATA_SET as EES_PERF_DATA_SET, OUT

YEAR = "2024-2025"
STATE_MAINSTREAM = {
    "AC": "Academy sponsor led",
    "ACC": "Academy converter",
    "CY": "Community school",
    "VA": "Voluntary aided",
    "VC": "Voluntary controlled",
    "FD": "Foundation school",
    "F": "Free school",
    "UTC": "University technical college",
    "SS": "Studio school",
    "CTC": "City technology college",
}
MIN_PUPILS = 30
TOP_N = 50
COLS = ["URN", "SCHNAME", "LEA", "NFTYPE", "RECTYPE", "EGENDER", "ADMPOL", "TPUP", "ATT8SCR", "P8MEA"]


def la_names():
    m = ees.meta(EES_PERF_DATA_SET)
    la = next(l for l in m["locations"] if l["level"]["code"] == "LA")
    return {o["oldCode"]: o["label"] for o in la["options"]}


def eligible():
    df = pd.read_csv(perf_tables.download(YEAR), dtype=str, encoding="utf-8-sig", usecols=COLS)
    counts = {"all rows": len(df)}
    df = df[df.RECTYPE == "1"]
    counts["mainstream (RECTYPE 1)"] = len(df)
    df = df[df.NFTYPE.isin(STATE_MAINSTREAM)]
    counts["state-funded (NFTYPE)"] = len(df)
    df = df.assign(TPUP=ees.to_num(df.TPUP), ATT8SCR=ees.to_num(df.ATT8SCR), P8MEA=ees.to_num(df.P8MEA))
    df = df[df.TPUP >= MIN_PUPILS]
    counts[f"TPUP >= {MIN_PUPILS}"] = len(df)
    df = df[df.ATT8SCR.notna()]
    counts["ATT8SCR not suppressed/missing"] = len(df)

    df["la_name"] = df.LEA.map(la_names())
    df["selective"] = df.ADMPOL.eq("SEL").map({True: "Selective", False: "Non-selective"})
    df["gender"] = df.EGENDER.str.title()
    return df, counts


def table(df, name):
    t = df.sort_values(["ATT8SCR", "SCHNAME"], ascending=[False, True]).head(TOP_N).copy()
    t.insert(0, "rank", t.ATT8SCR.rank(method="min", ascending=False).astype(int))
    t.insert(0, "table", name)
    return t.rename(columns={
        "SCHNAME": "school", "la_name": "local_authority", "ATT8SCR": "attainment8",
        "P8MEA": "progress8", "TPUP": "ks4_cohort", "ADMPOL": "admpol"})[
        ["table", "rank", "URN", "school", "local_authority", "attainment8", "progress8",
         "ks4_cohort", "gender", "selective", "admpol", "NFTYPE"]]


def main():
    df, counts = eligible()
    for k, v in counts.items():
        print(f"{k:35s} {v:>5}")
    print("EGENDER among eligible:", df.gender.value_counts().to_dict())
    print("ADMPOL among eligible:", df.ADMPOL.value_counts(dropna=False).to_dict())
    print("LEA codes without an LA name:", sorted(df[df.la_name.isna()].LEA.unique()))

    mixed = df[df.EGENDER == "MIXED"]
    tables = [
        table(mixed, "1. Top 50 mixed state schools"),
        table(mixed[mixed.ADMPOL != "SEL"], "2. Top 50 mixed non-selective state schools"),
        table(df, "3. Top 50 state schools, any gender"),
    ]
    out = pd.concat(tables, ignore_index=True)
    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / "league_tables_ks4_2024_25.csv", index=False)

    for t in tables:
        name = t.table.iloc[0]
        show = t.drop(columns=["table", "URN", "admpol", "NFTYPE"]).copy()
        show["attainment8"] = show.attainment8.map("{:.1f}".format)
        show["progress8"] = show.progress8.map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}")
        show["ks4_cohort"] = show.ks4_cohort.astype(int)
        show["school"] = show.school.str.slice(0, 48)
        print(f"\n### {name}")
        print(show.to_string(index=False))


if __name__ == "__main__":
    main()
