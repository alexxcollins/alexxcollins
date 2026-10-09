"""Latymer GCSE results split by sex vs leading selective girls' schools,
2022/23 to 2024/25. Source: EES API "Performance tables schools data"
(sex filter; every other characteristic filter pinned to Total)."""
import pandas as pd

import ees
from output1_high_pa_p8_2024 import DATA_SET, OUT

LATYMER = "102055"
GIRLS_SCHOOLS = {  # top 10 state girls' schools by 2024/25 A8, plus two near Enfield
    "138051": "Henrietta Barnett", "136615": "Tiffin Girls'", "136448": "Kendrick",
    "136551": "Newstead Wood", "136412": "Chelmsford County High", "137289": "Altrincham Girls'",
    "137515": "Colchester County High", "137235": "Stratford Girls'", "136795": "Nonsuch High",
    "136789": "Wallington High Girls'", "102852": "Woodford County High",
    "101361": "St Michael's Catholic GS",
}
PERIODS = ["2022/2023", "2023/2024", "2024/2025"]
IND = {"attainment8_average": "a8", "progress8_average": "p8", "progress8_lower_95_ci": "p8_low",
       "progress8_upper_95_ci": "p8_upp", "engmath_95_percent": "em5_pct",
       "ebacc_aps_average": "ebacc_aps", "pupil_count": "pupils"}


def main():
    m = ees.meta(DATA_SET)
    ind = {i["column"]: i["id"] for i in m["indicators"]}
    filt = {f["column"]: {o["label"]: o["id"] for o in f["options"]} for f in m["filters"]}
    sch = next(l for l in m["locations"] if l["level"]["code"] == "SCH")
    urns = {LATYMER, *GIRLS_SCHOOLS}
    locs = [{"level": "SCH", "id": o["id"]} for o in sch["options"] if o.get("urn") in urns]
    fids = list(filt["sex"].values()) + [o["Total"] for c, o in filt.items() if c != "sex"]
    rows, _ = ees.query(DATA_SET, {"and": [
        {"timePeriods": {"in": [{"period": p, "code": "AY"} for p in PERIODS]}},
        {"locations": {"in": locs}}, {"filters": {"in": fids}}]}, [ind[c] for c in IND])
    df = ees.results_to_frame(rows, m).rename(columns=IND)
    others = [c for c in filt if c != "sex"]
    df = df[(df[others] == "Total").all(axis=1)]
    df["time_period"] = df.time_period.str.replace(r"/20(\d\d)$", r"/\1", regex=True)

    lat = df[df.urn == LATYMER].copy()
    lat["unit"] = "Latymer – " + lat.sex.replace({"Total": "all pupils"}).str.lower()
    girls = df[(df.urn != LATYMER) & (df.sex == "Total")].copy()
    girls["unit"] = girls.urn.map(GIRLS_SCHOOLS)
    out = pd.concat([lat, girls])[["unit", "time_period", *IND.values()]]
    out.to_csv(OUT / "latymer_sex_split_vs_girls_schools.csv", index=False)

    # 3-year pupil-weighted means (P8: 2 years, none published for 2024/25)
    def wmean(d, col):
        d = d.dropna(subset=[col])
        return (d[col] * d.pupils).sum() / d.pupils.sum() if len(d) else float("nan")
    summ = out.groupby("unit").apply(lambda d: pd.Series({
        "a8_3y": wmean(d, "a8"), "a8_2025": d.loc[d.time_period == "2024/25", "a8"].mean(),
        "p8_2y": wmean(d, "p8"), "em5_3y": wmean(d, "em5_pct"),
        "ebacc_aps_3y": wmean(d, "ebacc_aps"), "pupils_per_year": d.pupils.mean()})).round(2)
    summ = summ.sort_values("a8_3y", ascending=False)
    with pd.option_context("display.width", 250):
        print(summ.to_string())
        print()
        print(out[out.unit.str.startswith("Latymer")].sort_values(["time_period", "unit"]).to_string(index=False))


if __name__ == "__main__":
    main()
