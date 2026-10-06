"""Output 1b: 3- and 5-year average Progress 8 for high-prior-attainment pupils.

P8 was not published for 2019/20 or 2020/21 (exams cancelled) or 2024/25
(no KS2 baseline), so the windows are the most recent years with P8:
  3-year: 2021/22, 2022/23, 2023/24
  5-year: 2017/18, 2018/19, 2021/22, 2022/23, 2023/24

Sources:
  2022/23, 2023/24  EES public API ("Performance tables schools data")
  2017/18, 2018/19, 2021/22  performance tables CSV downloads (not on EES)

Averaging: the headline figure is the pupil-weighted mean of the yearly
school P8 scores (weights = high-PA pupils in P8), i.e. the average P8 of
every high-PA pupil in the window. Each year's 95% CI is converted back to a
standard error, se = (upp - low) / (2 * 1.96), and combined as
se_avg = sqrt(sum(n^2 * se^2)) / sum(n). P8 is relative to each year's
national average, so the multi-year figure mixes slightly different
baselines; it is not an official DfE measure.
"""
import numpy as np
import pandas as pd

import perf_tables
from output1_high_pa_p8_2024 import OUT, SCHOOLS, fetch_school_rows

WINDOWS = {
    "3y": ["2021/22", "2022/23", "2023/24"],
    "5y": ["2017/18", "2018/19", "2021/22", "2022/23", "2023/24"],
}
API_YEARS = ["2022/2023", "2023/2024"]
CSV_YEARS = ["2017-2018", "2018-2019", "2021-2022"]
CROSS_CHECK_YEAR = "2022-2023"  # also in the API: used to verify the two sources agree
Z = 1.959964
VALUES = ["p8_avg", "p8_ci_low", "p8_ci_upp", "n_in_p8", "a8_avg", "n_pupils"]


def yearly_panel():
    api = fetch_school_rows(API_YEARS)
    api = api[api.prior_attainment == "High prior attainment"].copy()
    api["source"] = "EES API"
    csv = pd.concat([perf_tables.high_pa(y, list(SCHOOLS)) for y in CSV_YEARS])
    cols = ["urn", "time_period", "source", *VALUES]
    panel = pd.concat([api[cols], csv[cols]], ignore_index=True)

    # Every school x year, so absent years show as NaN rather than vanishing.
    years = sorted({y for w in WINDOWS.values() for y in w})
    full = pd.MultiIndex.from_product([list(SCHOOLS), years], names=["urn", "time_period"])
    panel = panel.set_index(["urn", "time_period"]).reindex(full).reset_index()
    panel.insert(1, "school", panel.urn.map(SCHOOLS))
    return panel


def cross_check():
    """Compare 2022/23 high-PA P8 between the API and the legacy CSV."""
    api = fetch_school_rows(["2022/2023"])
    api = api[api.prior_attainment == "High prior attainment"].set_index("urn")
    csv = perf_tables.high_pa(CROSS_CHECK_YEAR, list(SCHOOLS)).set_index("urn")
    diff = (api["p8_avg"] - csv["p8_avg"]).abs()
    n_diff = (api["n_in_p8"] - csv["n_in_p8"]).abs()
    print(f"Cross-check 2022/23 API vs CSV: max |P8 diff| = {diff.max():.3f}, "
          f"max |n diff| = {n_diff.max():.0f} over {diff.notna().sum()} schools")


def window_average(panel, years):
    p = panel[panel.time_period.isin(years)].dropna(subset=["p8_avg", "n_in_p8"]).copy()
    p["se"] = (p.p8_ci_upp - p.p8_ci_low) / (2 * Z)
    p["w_p8"] = p.n_in_p8 * p.p8_avg
    p["w2_se2"] = (p.n_in_p8 * p.se) ** 2
    p["w_a8"] = p.n_in_p8 * p.a8_avg
    g = p.groupby("urn")
    out = pd.DataFrame({
        "years_with_p8": g.size(),
        "years_used": g.time_period.agg(lambda s: ", ".join(sorted(s))),
        "n_in_p8": g.n_in_p8.sum(),
        "p8_wavg": g.w_p8.sum() / g.n_in_p8.sum(),
        "p8_mean_of_years": g.p8_avg.mean(),
        "a8_wavg": g.w_a8.sum() / g.n_in_p8.sum(),
    })
    se = np.sqrt(g.w2_se2.sum()) / g.n_in_p8.sum()
    out["p8_ci_low"] = out.p8_wavg - Z * se
    out["p8_ci_upp"] = out.p8_wavg + Z * se
    out = out.reindex(list(SCHOOLS))
    out["years_with_p8"] = out.years_with_p8.fillna(0).astype(int)
    out["complete_window"] = out.years_with_p8 == len(years)
    return out


def main():
    cross_check()
    panel = yearly_panel()

    summary = pd.DataFrame(index=pd.Index(list(SCHOOLS), name="urn"))
    summary["school"] = pd.Series(SCHOOLS)
    for name, years in WINDOWS.items():
        w = window_average(panel, years)
        summary = summary.join(w.add_prefix(f"hpa_{name}_"))
    for c in summary.columns:
        if c.endswith(("_wavg", "_mean_of_years", "_ci_low", "_ci_upp")):
            summary[c] = summary[c].round(2)
    summary = summary.sort_values("hpa_3y_p8_wavg", ascending=False, na_position="last")

    wide = panel.pivot(index="urn", columns="time_period", values="p8_avg")
    wide = wide.reindex(summary.index).add_prefix("hpa_p8_")

    OUT.mkdir(exist_ok=True)
    summary.reset_index().to_csv(OUT / "output1b_high_pa_p8_3y_5y.csv", index=False)
    panel.to_csv(OUT / "output1b_high_pa_p8_by_year.csv", index=False)

    show = ["school"] + [f"hpa_{w}_{c}" for w in WINDOWS
                         for c in ("p8_wavg", "p8_ci_low", "p8_ci_upp", "n_in_p8", "years_with_p8")]
    with pd.option_context("display.width", 250):
        print(summary[show].to_string())
        print()
        print(wide.join(summary.school).set_index("school").to_string())


if __name__ == "__main__":
    main()
