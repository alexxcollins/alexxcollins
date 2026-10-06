"""Top-end performance: GCSE grade 9 / 8+ / 7+ rates and GCSE subject breadth
(2024/25), and A level outcomes (2021/22-2024/25), for the comparison schools.

Sources (EES public API):
  GCSE grades by subject:  "Subject school level exam data"
                           1ae39901-b462-df76-b108-640a078d7944 (2024/25 only)
  16-18 / A level:         "Schools and colleges - performance"
                           019c2960-81e3-70c2-8d65-72c3718ae4fd

GCSE rates are shares of all GCSE (9-1) grades awarded (full course, plus
combined science double award counted as two grades), not shares of pupils.
Grade cells with suppressed counts are excluded from the numerator but kept
in the denominator ("Total exam entries"), so rates are lower bounds; the
number of suppressed cells is reported.
"""
import numpy as np
import pandas as pd

import ees
from output1_high_pa_p8_2024 import OUT, SCHOOLS

GCSE_DS = "1ae39901-b462-df76-b108-640a078d7944"
KS5_DS = "019c2960-81e3-70c2-8d65-72c3718ae4fd"
FULL = "GCSE (9-1) Full Course"
DOUBLE = "GCSE (9-1) Full Course (Double Award)"
Z = 1.959964


def school_locations(m, urns):
    sch = next(lvl for lvl in m["locations"] if lvl["level"]["code"] == "SCH")
    return {"locations": {"in": [{"level": "SCH", "id": o["id"]}
                                 for o in sch["options"] if o.get("urn") in urns]}}


def area_location(m, level, old_code=None):
    """All school rows inside an area. These data sets hold school rows only;
    LA / NAT exist just as parent locations, so this returns every school in it."""
    lvl = next(l for l in m["locations"] if l["level"]["code"] == level)
    o = next(o for o in lvl["options"] if old_code is None or o.get("oldCode") == old_code)
    return {"locations": {"in": [{"level": level, "id": o["id"]}]}}


BENCHMARKS = {"Hackney (all schools)": ("LA", "204"), "England (all schools)": ("NAT", None)}


def gcse_top_end():
    m = ees.meta(GCSE_DS)
    ind = {i["column"]: i["id"] for i in m["indicators"]}
    period = {"timePeriods": {"in": [{"period": "2024/2025", "code": "AY"}]}}
    inds = [ind["number_achieving"], ind["pupil_count"]]
    rows, _ = ees.query(GCSE_DS, {"and": [period, school_locations(m, set(SCHOOLS))]}, inds, page_size=5000)
    df = ees.results_to_frame(rows, m)
    df["unit"] = df.urn.map(SCHOOLS)
    df["geographic_level"] = "SCH"
    raw = df.copy()
    for name, (level, code) in BENCHMARKS.items():
        brows, _ = ees.query(GCSE_DS, {"and": [period, area_location(m, level, code)]}, inds, page_size=5000)
        b = ees.results_to_frame(brows, m)
        b["unit"] = name
        b["geographic_level"] = "AREA"
        df = pd.concat([df, b], ignore_index=True)
    df = df[df.qualification_detailed.isin([FULL, DOUBLE])]

    totals = df[df.grade == "Total exam entries"].copy()
    totals["grades_awarded"] = totals.number_achieving * np.where(
        totals.qualification_detailed == DOUBLE, 2, 1)

    g = df[df.grade.str.fullmatch(r"\d{1,2}")].copy()
    g["suppressed"] = g.number_achieving.isna()
    # Split each grade label into its digits (double award "98" -> 9 and 8)
    g["digits"] = g.grade.apply(lambda s: [int(c) for c in s])
    g = g.explode("digits")
    g["n"] = g.number_achieving
    for k in (9, 8, 7, 4):
        g[f"n_{k}plus"] = g.n.where(g.digits >= k, 0)

    def summarise(sel_g, sel_t):
        a = sel_g.groupby("unit")[["n_9plus", "n_8plus", "n_7plus", "n_4plus"]].sum()
        a["grades_awarded"] = sel_t.groupby("unit").grades_awarded.sum()
        out = pd.DataFrame(index=a.index)
        for k in (9, 8, 7, 4):
            out[f"pct_grades_{k}plus"] = (100 * a[f"n_{k}plus"] / a.grades_awarded).round(1)
        out["grades_awarded"] = a.grades_awarded
        return out

    allsub = summarise(g, totals)
    allsub["suppressed_grade_cells"] = g.drop_duplicates(["unit", "subject", "qualification_detailed", "grade"]) \
        .groupby("unit").suppressed.sum()

    for subj, tag in (("Mathematics", "maths"), ("English Language", "eng_lang")):
        s = summarise(g[g.subject == subj], totals[totals.subject == subj])
        allsub[f"{tag}_pct_9"] = s["pct_grades_9plus"]
        allsub[f"{tag}_pct_7plus"] = s["pct_grades_7plus"]

    # pupil_count repeats on every row of a school: one value per school, then sum
    pupils = df.drop_duplicates(["unit", "urn"]).groupby("unit").pupil_count.sum()
    allsub["ks4_pupils"] = pupils
    allsub["gcse_grades_per_pupil"] = (allsub.grades_awarded / pupils).round(1)

    # Breadth: distinct GCSE subjects with any entries (school rows only)
    t_sch = totals[totals.geographic_level == "SCH"].copy()
    t_sch = t_sch[t_sch.number_achieving.fillna(1) > 0]
    allsub["gcse_subjects_offered"] = t_sch.groupby("unit").subject.nunique()
    subj_lists = t_sch.groupby("unit").subject.agg(lambda s: "; ".join(sorted(set(s))))
    allsub["gcse_subjects"] = subj_lists
    # Non-GCSE KS4 qualifications on the books (e.g. graded music exams, BTECs)
    other = raw[~raw.qualification_detailed.isin([FULL, DOUBLE]) & (raw.grade == "Total exam entries")]
    allsub["other_ks4_quals"] = other.groupby("unit").apply(
        lambda d: "; ".join(f"{q} – {s} ({'' if pd.isna(n) else int(n)})"
                            for q, s, n in zip(d.qualification_detailed, d.subject, d.number_achieving)))
    return allsub.sort_values("pct_grades_9plus", ascending=False), t_sch


def a_level():
    m = ees.meta(KS5_DS)
    ind = {i["column"]: i["id"] for i in m["indicators"]}
    filt = {f["column"]: {o["label"]: o["id"] for o in f["options"]} for f in m["filters"]}
    want = ["aps_per_entry", "aps_per_entry_grade", "best_three_alevels_aps", "best_three_alevels_grade",
            "aab_percent", "value_added", "value_added_lower_ci", "value_added_upper_ci",
            "progress_banding", "aps_per_entry_student_count", "end1618_student_count"]
    crit = {"and": [school_locations(m, set(SCHOOLS)),
                    {"filters": {"in": [filt["exam_cohort"]["A level"]]}},
                    {"filters": {"in": [filt["disadvantage_status"]["Total"]]}}]}
    rows, _ = ees.query(KS5_DS, crit, [ind[c] for c in want])
    df = ees.results_to_frame(rows, m)
    df["unit"] = df.urn.map(SCHOOLS)
    for c in ("aps_per_entry_grade", "best_three_alevels_grade", "progress_banding"):
        if c in df:  # text indicators: undo the numeric coercion
            df[c] = [r["values"].get(ind[c]) for r in rows]
    df = pd.concat([df, national_a_level()], ignore_index=True)
    df["time_period"] = df.time_period.str.replace(r"/20(\d\d)$", r"/\1", regex=True)
    df = df.sort_values(["unit", "time_period"])

    # A level value added is only published from 2023/24, so this pools 2 years
    v = df.dropna(subset=["value_added", "aps_per_entry_student_count"]).copy()
    v = v.sort_values("time_period")
    v["se"] = (v.value_added_upper_ci - v.value_added_lower_ci) / (2 * Z)
    v["n"] = v.aps_per_entry_student_count
    gv = v.groupby("unit")
    pooled = pd.DataFrame({
        "years": gv.size(),
        "a_level_students": gv.n.sum(),
        "va_2y_wavg": (gv.apply(lambda d: (d.n * d.value_added).sum()) / gv.n.sum()).round(2),
        "aps_per_entry_2y_wavg": (gv.apply(lambda d: (d.n * d.aps_per_entry).sum()) / gv.n.sum()).round(1),
        "aab_pct_2024_25": gv.aab_percent.last().round(1),
    })
    se = np.sqrt(gv.apply(lambda d: ((d.n * d.se) ** 2).sum())) / gv.n.sum()
    pooled["va_ci_low"] = (pooled.va_2y_wavg - Z * se).round(2)
    pooled["va_ci_upp"] = (pooled.va_2y_wavg + Z * se).round(2)
    return df, pooled.sort_values("aps_per_entry_2y_wavg", ascending=False)


NAT_KS5_DS = "019d015a-342c-741d-9c0f-704971228b32"


def national_a_level():
    """England benchmark (all state-funded schools and colleges), A level cohort."""
    m = ees.meta(NAT_KS5_DS)
    ind = {i["column"]: i["id"] for i in m["indicators"]}
    filt = {f["column"]: {o["label"]: o["id"] for o in f["options"]} for f in m["filters"]}
    want = ["aps_per_entry", "aps_per_entry_grade", "best_three_alevels_grade", "aab_percent"]
    crit = {"and": [{"geographicLevels": {"eq": "NAT"}},
                    {"filters": {"in": [filt["exam_cohort"]["A level"]]}},
                    {"filters": {"in": [filt["disadvantage_status"]["Total"]]}},
                    {"filters": {"in": [filt["establishment_type"]["All state-funded schools and colleges"]]}}]}
    rows, _ = ees.query(NAT_KS5_DS, crit, [ind[c] for c in want])
    df = ees.results_to_frame(rows, m)
    for c in ("aps_per_entry_grade", "best_three_alevels_grade"):
        df[c] = [r["values"].get(ind[c]) for r in rows]
    df["unit"] = "England (state-funded)"
    return df


def main():
    gcse, subj = gcse_top_end()
    ks5_years, ks5_pooled = a_level()
    OUT.mkdir(exist_ok=True)
    gcse.to_csv(OUT / "top_end_gcse_2024_25.csv")
    ks5_years.to_csv(OUT / "a_level_by_year.csv", index=False)
    ks5_pooled.to_csv(OUT / "a_level_2y_summary.csv")
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        cols = ["pct_grades_9plus", "pct_grades_8plus", "pct_grades_7plus", "pct_grades_4plus",
                "maths_pct_9", "maths_pct_7plus", "eng_lang_pct_9", "eng_lang_pct_7plus",
                "ks4_pupils", "gcse_grades_per_pupil", "gcse_subjects_offered", "suppressed_grade_cells"]
        print(gcse[cols].to_string())
        print()
        print(gcse[["gcse_subjects", "other_ks4_quals"]].to_string())
        print()
        print(ks5_pooled.to_string())
        print()
        print(ks5_years[["unit", "time_period", "aps_per_entry_grade", "best_three_alevels_grade",
                         "aab_percent", "value_added", "value_added_lower_ci", "value_added_upper_ci",
                         "aps_per_entry_student_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
