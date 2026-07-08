from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.anomaly import anomaly_scores
from analytics.checker import checker_analysis
from analytics.correlation import correlation_matrix
from analytics.department import department_analysis
from analytics.employee import employee_analysis
from analytics.spc import spc_tables
from analytics.statistics import descriptive_stats, frequency_percentages
from analytics.trends import time_trend
from charts.bar import bar_count
from charts.control_chart import control_chart
from charts.heatmap import cross_heatmap
from charts.histogram import histogram
from charts.pareto_chart import pareto_figure
from charts.pie import pie_distribution
from charts.scatter import scatter_plot
from config import APP_CONFIG, CANONICAL_FIELDS, DISPLAY_NAMES
from data.cleaner import apply_column_mapping
from data.detector import detect_columns
from data.loader import load_excel_workbook
from exports.excel import export_excel
from exports.pdf import export_pdf


st.set_page_config(page_title=APP_CONFIG.app_title, layout=APP_CONFIG.default_page_layout)
st.title(APP_CONFIG.app_title)
st.caption("Fully local and offline. No AI models, cloud APIs, or internet services.")


@st.cache_data(show_spinner=False)
def cached_load_excel(file_bytes: bytes) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    return load_excel_workbook(file_bytes)


@st.cache_data(show_spinner=False)
def cached_clean(raw_df: pd.DataFrame, mapping_items: Tuple[Tuple[str, Optional[str]], ...]) -> pd.DataFrame:
    mapping = dict(mapping_items)
    return apply_column_mapping(raw_df, mapping)


def render_kpis(df: pd.DataFrame) -> Dict[str, float]:
    total_discrepancies = int(len(df))
    total_jobs = int(df["job_number"].nunique())
    total_assemblers = int(df["assembler"].nunique())
    total_checkers = int(df["checker"].nunique())
    total_rework = int(df["rework"].nunique())
    total_departments = int(df["department"].nunique())
    avg_per_job = round(total_discrepancies / max(total_jobs, 1), 2)
    avg_per_assembler = round(total_discrepancies / max(total_assemblers, 1), 2)
    avg_per_month = round(total_discrepancies / max(df["year_month"].nunique(), 1), 2)
    avg_cost = round(float(pd.to_numeric(df["cost"], errors="coerce").mean()), 2)

    kpis = {
        "Total Discrepancies": total_discrepancies,
        "Total Jobs": total_jobs,
        "Total Assemblers": total_assemblers,
        "Total Checkers": total_checkers,
        "Total Rework Personnel": total_rework,
        "Total Departments": total_departments,
        "Average Discrepancies per Job": avg_per_job,
        "Average Discrepancies per Assembler": avg_per_assembler,
        "Average Discrepancies per Month": avg_per_month,
        "Average Repair Cost": 0.0 if np.isnan(avg_cost) else avg_cost,
    }

    cols = st.columns(5)
    for idx, (name, value) in enumerate(kpis.items()):
        cols[idx % 5].metric(name, value)
    return kpis


def filter_frame(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    working = df.copy()

    if working["date"].notna().any():
        min_date = working["date"].min().date()
        max_date = working["date"].max().date()
        selected = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(selected, tuple) and len(selected) == 2:
            start, end = selected
            working = working[(working["date"] >= pd.Timestamp(start)) & (working["date"] <= pd.Timestamp(end))]

    selectable_columns = [
        "assembler",
        "checker",
        "rework",
        "department",
        "category",
        "severity",
        "project",
        "customer",
        "job_number",
        "shift",
    ]
    for col in selectable_columns:
        options = sorted(working[col].dropna().astype(str).unique().tolist())
        selected_values = st.sidebar.multiselect(DISPLAY_NAMES[col], options=options, default=[])
        if selected_values:
            working = working[working[col].isin(selected_values)]
    return working


def render_upload_mapping() -> Optional[pd.DataFrame]:
    st.subheader("1) Upload and Column Mapping")
    uploaded = st.file_uploader("Upload discrepancy Excel workbook", type=["xlsx", "xlsm", "xls"])
    if not uploaded:
        st.info("Upload an Excel file to begin analysis.")
        return None

    file_bytes = uploaded.getvalue()
    raw_df, sheets = cached_load_excel(file_bytes)
    if raw_df.empty:
        st.warning("No usable rows were found in this workbook.")
        return None

    st.success(f"Loaded {len(raw_df):,} rows from {len(sheets)} sheet(s).")
    detected = detect_columns(raw_df.columns.tolist())

    st.markdown("Detected columns (adjust if needed):")
    mapped: Dict[str, Optional[str]] = {}
    all_columns = ["<Not Available>"] + raw_df.columns.tolist()

    col_a, col_b = st.columns(2)
    fields = list(CANONICAL_FIELDS.keys())
    for i, field in enumerate(fields):
        holder = col_a if i % 2 == 0 else col_b
        default = detected.get(field)
        default_index = all_columns.index(default) if default in all_columns else 0
        chosen = holder.selectbox(
            f"{DISPLAY_NAMES[field]} column",
            options=all_columns,
            index=default_index,
            key=f"map_{field}",
        )
        mapped[field] = None if chosen == "<Not Available>" else chosen

    with st.expander("Detected column overview", expanded=False):
        st.write(pd.DataFrame({"Canonical Field": list(mapped.keys()), "Mapped Column": list(mapped.values())}))
        st.write("Workbook columns:", raw_df.columns.tolist())

    clean_df = cached_clean(raw_df, tuple(mapped.items()))
    missing = [DISPLAY_NAMES[f] for f, c in mapped.items() if c is None]
    if missing:
        st.warning(f"Missing columns are handled gracefully: {', '.join(missing)}")
    return clean_df


def render_overview_tab(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    st.subheader("2) Dashboard")
    kpis = render_kpis(df)
    stats_table = pd.DataFrame(
        {
            "Metric": ["Cost", "Repair Time", "Defects per Job"],
            "Count": [
                descriptive_stats(df["cost"]).get("count", 0),
                descriptive_stats(df["repair_time"]).get("count", 0),
                descriptive_stats(df.groupby("job_number")["record_id"].count()).get("count", 0),
            ],
            "Mean": [
                descriptive_stats(df["cost"]).get("mean", 0),
                descriptive_stats(df["repair_time"]).get("mean", 0),
                descriptive_stats(df.groupby("job_number")["record_id"].count()).get("mean", 0),
            ],
            "Median": [
                descriptive_stats(df["cost"]).get("median", 0),
                descriptive_stats(df["repair_time"]).get("median", 0),
                descriptive_stats(df.groupby("job_number")["record_id"].count()).get("median", 0),
            ],
            "Std Dev": [
                descriptive_stats(df["cost"]).get("std", 0),
                descriptive_stats(df["repair_time"]).get("std", 0),
                descriptive_stats(df.groupby("job_number")["record_id"].count()).get("std", 0),
            ],
        }
    )
    st.dataframe(stats_table, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    fig_pareto_assembler = pareto_figure(df, "assembler", "Pareto by Assembler")
    fig_pareto_category = pareto_figure(df, "category", "Pareto by Category")
    if fig_pareto_assembler:
        c1.plotly_chart(fig_pareto_assembler, use_container_width=True)
    if fig_pareto_category:
        c2.plotly_chart(fig_pareto_category, use_container_width=True)

    monthly = time_trend(df, "monthly")
    if not monthly.empty:
        line = px.line(monthly, x="period", y="count", title="Monthly Trend", markers=True)
        st.plotly_chart(line, use_container_width=True)

    heat = cross_heatmap(df, "category", "department", "Department x Category Heatmap")
    if heat:
        st.plotly_chart(heat, use_container_width=True)

    st.markdown("### Detailed Data Table")
    search = st.text_input("Search in Description / Comments")
    shown = df.copy()
    if search:
        pattern = search.lower()
        shown = shown[
            shown["description"].str.lower().str.contains(pattern, na=False)
            | shown["comments"].str.lower().str.contains(pattern, na=False)
        ]
    st.dataframe(shown, use_container_width=True)
    return {"kpis": pd.DataFrame(list(kpis.items()), columns=["KPI", "Value"]), "stats": stats_table}


def render_analysis_tabs(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    tabs = st.tabs(
        [
            "Overview",
            "Assembler Analysis",
            "Checker Analysis",
            "Rework Analysis",
            "Job Analysis",
            "Department Analysis",
            "Root Cause",
            "Cost / Time",
            "SPC Control Charts",
            "Anomalies",
            "Reports",
        ]
    )

    export_tables: Dict[str, pd.DataFrame] = {}
    with tabs[0]:
        export_tables.update(render_overview_tab(df))

        st.markdown("### Core Bar Charts")
        bar_fields = ["assembler", "checker", "department", "category", "root_cause", "severity", "customer"]
        for field in bar_fields:
            fig = bar_count(df, field, f"Discrepancies by {DISPLAY_NAMES[field]}")
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Time Trends")
        trend_cols = st.columns(3)
        for i, period in enumerate(["weekly", "daily", "quarterly"]):
            trend_df = time_trend(df, period)
            if not trend_df.empty:
                trend_fig = px.line(trend_df, x="period", y="count", markers=True, title=f"{period.title()} Trend")
                trend_cols[i].plotly_chart(trend_fig, use_container_width=True)

        st.markdown("### Pie Distributions")
        pie_cols = st.columns(4)
        for i, field in enumerate(["severity", "category", "department", "shift"]):
            fig = pie_distribution(df, field, f"{DISPLAY_NAMES[field]} Distribution")
            if fig:
                pie_cols[i].plotly_chart(fig, use_container_width=True)

        st.markdown("### Histograms")
        h_cols = st.columns(3)
        defect_per_job = df.groupby("job_number")["record_id"].count().rename("defects_per_job").reset_index()
        for idx, (source_df, col, title) in enumerate(
            [
                (df, "repair_time", "Repair Time Distribution"),
                (df, "cost", "Repair Cost Distribution"),
                (defect_per_job, "defects_per_job", "Defects per Job Distribution"),
            ]
        ):
            fig = histogram(source_df, col, title)
            if fig:
                h_cols[idx].plotly_chart(fig, use_container_width=True)

        st.markdown("### Heatmaps")
        for x_col, y_col, title in [
            ("category", "assembler", "Assembler x Category"),
            ("department", "assembler", "Assembler x Department"),
            ("category", "checker", "Checker x Category"),
            ("category", "year_month", "Month x Category"),
        ]:
            fig = cross_heatmap(df, x_col, y_col, title)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Scatter & Box Plots")
        scatter_cols = st.columns(3)
        for idx, (x_col, y_col, title) in enumerate(
            [
                ("cost", "repair_time", "Cost vs Repair Time"),
                ("cost", "record_id", "Cost vs Defect Record"),
                ("repair_time", "record_id", "Repair Time vs Defect Record"),
            ]
        ):
            fig = scatter_plot(df, x_col, y_col, title, color="severity")
            if fig:
                scatter_cols[idx].plotly_chart(fig, use_container_width=True)

        for field in ["assembler", "department", "category"]:
            box_fig = px.box(df, x=field, y="cost", title=f"Cost Outliers by {DISPLAY_NAMES[field]}")
            st.plotly_chart(box_fig, use_container_width=True)

        tree = (
            df.groupby(["department", "category", "root_cause"])["record_id"].count().reset_index(name="count")
        )
        if not tree.empty:
            st.plotly_chart(
                px.treemap(tree, path=["department", "category", "root_cause"], values="count", title="Defect Treemap"),
                use_container_width=True,
            )

    with tabs[1]:
        emp_table = employee_analysis(df)
        st.dataframe(emp_table, use_container_width=True)
        export_tables["employee_analysis"] = emp_table

    with tabs[2]:
        chk_table = checker_analysis(df)
        st.dataframe(chk_table, use_container_width=True)
        export_tables["checker_analysis"] = chk_table

    with tabs[3]:
        rework_freq = frequency_percentages(df, "rework")
        st.dataframe(rework_freq, use_container_width=True)
        trend = (
            df.groupby(["year_month", "rework"])["record_id"]
            .count()
            .reset_index(name="repair_frequency")
            .sort_values("repair_frequency", ascending=False)
        )
        st.dataframe(trend, use_container_width=True)
        export_tables["rework_frequency"] = rework_freq
        export_tables["rework_trend"] = trend

    with tabs[4]:
        defects_by_job = df.groupby("job_number")["record_id"].count().reset_index(name="discrepancies")
        top_jobs = defects_by_job.sort_values("discrepancies", ascending=False).head(APP_CONFIG.top_n_rankings)
        st.markdown("Top 20 Jobs by Discrepancies")
        st.dataframe(top_jobs, use_container_width=True)

        if pd.to_numeric(df["cost"], errors="coerce").notna().any():
            cost_jobs = df.groupby("job_number")["cost"].sum().reset_index(name="total_cost")
            st.markdown("Jobs by Repair Cost")
            st.dataframe(cost_jobs.sort_values("total_cost", ascending=False).head(APP_CONFIG.top_n_rankings), use_container_width=True)
            export_tables["job_costs"] = cost_jobs

        recurring = (
            df.groupby(["job_number", "category"])["record_id"]
            .count()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(APP_CONFIG.top_n_rankings)
        )
        st.markdown("Highest Recurring Job Defects")
        st.dataframe(recurring, use_container_width=True)
        export_tables["top_jobs"] = top_jobs
        export_tables["recurring_job_defects"] = recurring

    with tabs[5]:
        dept = department_analysis(df)
        st.dataframe(dept, use_container_width=True)
        export_tables["department_analysis"] = dept

    with tabs[6]:
        root_freq = frequency_percentages(df, "root_cause")
        st.dataframe(root_freq, use_container_width=True)
        root_pareto = pareto_figure(df, "root_cause", "Root Cause Pareto")
        if root_pareto:
            st.plotly_chart(root_pareto, use_container_width=True)
        root_trend = (
            df.groupby(["year_month", "root_cause"])["record_id"]
            .count()
            .reset_index(name="count")
            .sort_values(["year_month", "count"], ascending=[True, False])
        )
        st.dataframe(root_trend, use_container_width=True)
        export_tables["root_cause_frequency"] = root_freq

    with tabs[7]:
        if pd.to_numeric(df["cost"], errors="coerce").notna().any():
            st.metric("Total Cost", round(float(pd.to_numeric(df["cost"], errors="coerce").sum()), 2))
            st.metric("Average Cost", round(float(pd.to_numeric(df["cost"], errors="coerce").mean()), 2))

            c_cols = st.columns(3)
            cost_by_assembler = df.groupby("assembler")["cost"].sum().sort_values(ascending=False).reset_index()
            cost_by_department = df.groupby("department")["cost"].sum().sort_values(ascending=False).reset_index()
            cost_by_category = df.groupby("category")["cost"].sum().sort_values(ascending=False).reset_index()
            c_cols[0].plotly_chart(px.bar(cost_by_assembler, x="assembler", y="cost", title="Cost by Assembler"), use_container_width=True)
            c_cols[1].plotly_chart(px.bar(cost_by_department, x="department", y="cost", title="Cost by Department"), use_container_width=True)
            c_cols[2].plotly_chart(px.bar(cost_by_category, x="category", y="cost", title="Cost by Category"), use_container_width=True)
            monthly_cost = df.groupby("year_month")["cost"].sum().reset_index(name="total_cost")
            st.plotly_chart(px.line(monthly_cost, x="year_month", y="total_cost", title="Monthly Cost Trend"), use_container_width=True)
            export_tables["monthly_cost"] = monthly_cost
        else:
            st.warning("No usable cost column available.")

    with tabs[8]:
        spc = spc_tables(df)
        if not spc:
            st.warning("SPC charts require valid date and job/discrepancy data.")
        else:
            for label, table in spc.items():
                y_col = "count" if label == "c" else label
                fig = control_chart(table, "period", y_col, f"{label.upper()} Chart")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(table, use_container_width=True)
                export_tables[f"{label}_chart_data"] = table

    with tabs[9]:
        anomaly_table = anomaly_scores(df, contamination=APP_CONFIG.anomaly_contamination)
        if anomaly_table.empty:
            st.warning("Insufficient numeric data for anomaly detection.")
        else:
            flagged = anomaly_table[anomaly_table["anomaly_flag"]]
            st.markdown("Unusual records")
            st.dataframe(flagged.head(200), use_container_width=True)
            st.markdown("Unusual jobs")
            st.dataframe(flagged["job_number"].value_counts().reset_index(), use_container_width=True)
            st.markdown("Unusual assemblers")
            st.dataframe(flagged["assembler"].value_counts().reset_index(), use_container_width=True)
            st.markdown("Unusual departments")
            st.dataframe(flagged["department"].value_counts().reset_index(), use_container_width=True)
            export_tables["anomalies"] = flagged

    with tabs[10]:
        corr = correlation_matrix(df)
        if not corr.empty:
            st.plotly_chart(px.imshow(corr, text_auto=True, title="Correlation Heatmap"), use_container_width=True)
            export_tables["correlation"] = corr.reset_index()

        st.markdown("### Export")
        export_tables["filtered_data"] = df
        pdf_bytes = export_pdf(APP_CONFIG.app_title, render_kpis(df))
        excel_bytes = export_excel(export_tables)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Export PDF Report", data=pdf_bytes, file_name="manufacturing_report.pdf")
        st.download_button(
            "Export Excel Report",
            data=excel_bytes,
            file_name="manufacturing_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button("Export Filtered Data (CSV)", data=csv_bytes, file_name="filtered_data.csv", mime="text/csv")

        st.write("Export Charts (PNG):")
        example_fig = pareto_figure(df, "category", "Pareto by Category")
        if example_fig:
            try:
                png_bytes = example_fig.to_image(format="png")
                st.download_button("Export Example Chart PNG", data=png_bytes, file_name="pareto_category.png")
            except Exception:
                st.warning("PNG export requires plotly image engine support in local environment.")

    return export_tables


def main() -> None:
    st.sidebar.markdown("### Local Dashboard")
    st.sidebar.write("Use the uploader and mapping panel, then filter data live.")
    cleaned = render_upload_mapping()
    if cleaned is None or cleaned.empty:
        st.stop()
    filtered = filter_frame(cleaned)
    if filtered.empty:
        st.warning("No records after filtering. Adjust filter values.")
        st.stop()
    render_analysis_tabs(filtered)


if __name__ == "__main__":
    main()
