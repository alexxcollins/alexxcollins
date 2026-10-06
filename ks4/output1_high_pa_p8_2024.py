"""Output 1: Progress 8 for high-prior-attainment pupils, 2023/24, selected schools.

Source: EES public API, "Performance tables schools data" (Key stage 4
performance publication), data set 19e39901-a96c-be76-b9c2-6af54ae076d2.
This is the API-published version of the KS4 institution-level performance
file; the data-catalogue IDs c8f753ef-... / d7ce19cb-... are not exposed by
the API (404), so this data set is used instead.
"""
from pathlib import Path

import pandas as pd

import ees

DATA_SET = "19e39901-a96c-be76-b9c2-6af54ae076d2"
PERIOD = {"period": "2023/2024", "code": "AY"}

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

INDICATORS = {
    "progress8_average": "p8_avg",
    "progress8_lower_95_ci": "p8_ci_low",
    "progress8_upper_95_ci": "p8_ci_upp",
    "progress8_pupil_count": "n_in_p8",
    "attainment8_average": "a8_avg",
    "pupil_count": "n_pupils",
}

OUT = Path(__file__).parent / "output"

# National benchmark: "National characteristics by school types data"
NATIONAL_DATA_SET = "18e39901-7fe3-8372-8b2b-33f7ae1e1d12"


def national_high_pa_p8():
    """National high-prior-attainment P8 for state-funded mainstream (or all state-funded) schools."""
    m = ees.meta(NATIONAL_DATA_SET)
    ind = {i["column"]: i["id"] for i in m["indicators"]}
    filt = {f["column"]: {o["label"]: o["id"] for o in f["options"]} for f in m["filters"]}
    rows, _ = ees.query(
        NATIONAL_DATA_SET,
        {"and": [{"timePeriods": {"in": [PERIOD]}},
                 {"geographicLevels": {"eq": "NAT"}},
                 {"filters": {"in": [filt["prior_attainment"]["High prior attainment"]]}}]},
        [ind["progress8_average"], ind["attainment8_average"]],
    )
    df = ees.results_to_frame(rows, m)
    others = [c for c in filt if c not in ("prior_attainment", "establishment_type_group")]
    df = df[(df[others] == "Total").all(axis=1)].set_index("establishment_type_group")
    for grp in ("State-funded mainstream", "All state-funded"):
        if grp in df.index:
            return grp, df.loc[grp, "progress8_average"], df.loc[grp, "attainment8_average"]
    raise RuntimeError(f"No state-funded group in {list(df.index)}")


def main():
    m = ees.meta(DATA_SET)
    ind_ids = {i["column"]: i["id"] for i in m["indicators"]}
    filt = {f["column"]: {o["label"]: o["id"] for o in f["options"]} for f in m["filters"]}

    # Every non-prior-attainment filter pinned to Total; prior attainment High + Total.
    filter_ids = [filt["prior_attainment"]["High prior attainment"],
                  filt["prior_attainment"]["Total"]]
    filter_ids += [opts["Total"] for col, opts in filt.items() if col != "prior_attainment"]

    criteria = {
        "and": [
            {"timePeriods": {"in": [PERIOD]}},
            {"locations": {"in": [{"level": "SCH", "urn": u} for u in SCHOOLS]}},
            {"filters": {"in": filter_ids}},
        ]
    }
    rows, warnings = ees.query(DATA_SET, criteria, [ind_ids[c] for c in INDICATORS])
    if warnings:
        print("API warnings:", warnings)
    df = ees.results_to_frame(rows, m)

    # Keep rows where all other characteristic filters are Total.
    others = [c for c in filt if c != "prior_attainment"]
    df = df[(df[others] == "Total").all(axis=1)]
    df = df.rename(columns=INDICATORS)

    hi = df[df.prior_attainment == "High prior attainment"].set_index("urn")
    al = df[df.prior_attainment == "Total"].set_index("urn")

    out = pd.DataFrame(index=pd.Index(list(SCHOOLS), name="urn"))
    out["school"] = pd.Series(SCHOOLS)
    out["la_name"] = hi["la_name"].reindex(out.index).fillna(al["la_name"].reindex(out.index))
    for c in INDICATORS.values():
        out[f"hpa_{c}"] = hi[c].reindex(out.index)
    out["all_p8_avg"] = al["p8_avg"].reindex(out.index)
    out["all_n_pupils"] = al["n_pupils"].reindex(out.index)
    out["hpa_share_of_cohort"] = (out["hpa_n_pupils"] / out["all_n_pupils"]).round(3)
    # DfE school P8 CIs are interpreted against 0 (the all-pupil national average).
    out["hpa_p8_ci_vs_zero"] = pd.Series(pd.NA, index=out.index, dtype="object")
    out.loc[out.hpa_p8_ci_low > 0, "hpa_p8_ci_vs_zero"] = "above 0"
    out.loc[out.hpa_p8_ci_upp < 0, "hpa_p8_ci_vs_zero"] = "below 0"
    out.loc[(out.hpa_p8_ci_low <= 0) & (out.hpa_p8_ci_upp >= 0), "hpa_p8_ci_vs_zero"] = "spans 0"
    grp, nat_p8, nat_a8 = national_high_pa_p8()
    print(f"National high-PA benchmark ({grp}): P8 {nat_p8}, A8 {nat_a8}")
    out["national_hpa_p8_avg"] = nat_p8
    out["national_hpa_a8_avg"] = nat_a8
    out["hpa_p8_minus_national_hpa"] = (out["hpa_p8_avg"] - nat_p8).round(2)
    out["time_period"] = "2023/24"
    out["source_data_set"] = DATA_SET
    out = out.sort_values("hpa_p8_avg", ascending=False, na_position="last")

    missing = [u for u in SCHOOLS if u not in hi.index]
    if missing:
        print("No high-prior-attainment row returned for:", missing)

    OUT.mkdir(exist_ok=True)
    out.reset_index().to_csv(OUT / "output1_high_pa_p8_2023_24.csv", index=False)
    print(out.drop(columns=["source_data_set", "time_period"]).to_string())


if __name__ == "__main__":
    main()
