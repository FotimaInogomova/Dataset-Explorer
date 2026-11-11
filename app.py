import io
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


MAX_UPLOAD_SIZE_MB = 5


def is_comparison_missing(value):
    """Treat empty and whitespace-only CSV cells as missing for comparison."""
    return isinstance(value, str) and (value == "" or value.strip() == "")


def read_comparison_csv(uploaded_file, separator):
    """Read a separate text-preserving view without pandas' default NA conversion."""
    return pd.read_csv(
        io.BytesIO(uploaded_file.getvalue()),
        sep=separator,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        header=0,
    )


def comparison_missing_mask(frame):
    return frame.apply(lambda column: column.map(is_comparison_missing))


def comparison_value(value):
    """Canonicalize blank cells only for matching row values; keep source text intact."""
    return None if is_comparison_missing(value) else value


def read_experiment_json(uploaded_file):
    if Path(uploaded_file.name).suffix.lower() != ".json":
        raise ValueError("Choose a .json experiment summary file.")
    try:
        record = json.loads(uploaded_file.getvalue().decode("utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ValueError("The file is not valid UTF-8 JSON.") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON near line {error.lineno}, column {error.colno}.") from error
    if not isinstance(record, dict):
        raise ValueError("The JSON root must be one experiment summary object.")
    if "format_version" in record and record["format_version"] != 1:
        raise ValueError("Unsupported experiment summary format. Expected format_version 1.")
    return record


def is_finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(number)


def is_finite_metric(value):
    return is_finite_number(value) and 0 <= float(value) <= 1


def is_known_context_value(field, value):
    if field in {"format_version", "seed"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if field == "features":
        return isinstance(value, list) and all(isinstance(feature, str) for feature in value)
    if field == "threshold":
        return is_finite_number(value)
    return isinstance(value, str) and bool(value.strip())


def normalized_experiment_context(field, value):
    return tuple(sorted(set(value))) if field == "features" else value


def experiment_context_status(record_a, record_b):
    context_fields = (
        "format_version",
        "dataset_id",
        "split_id",
        "target",
        "positive_class",
        "features",
        "threshold",
        "seed",
        "evaluation_split",
    )
    missing = []
    differences = []
    for field in context_fields:
        if field not in record_a or not is_known_context_value(field, record_a.get(field)):
            missing.append(f"A: {field}")
        if field not in record_b or not is_known_context_value(field, record_b.get(field)):
            missing.append(f"B: {field}")
        if field not in record_a or field not in record_b:
            continue
        if not is_known_context_value(field, record_a[field]) or not is_known_context_value(
            field, record_b[field]
        ):
            continue
        value_a = normalized_experiment_context(field, record_a[field])
        value_b = normalized_experiment_context(field, record_b[field])
        if value_a != value_b:
            differences.append(f"{field}: A = {record_a[field]!r}; B = {record_b[field]!r}")
        if field == "evaluation_split":
            if record_a[field] != "validation":
                differences.append(f"A evaluation_split is {record_a[field]!r}, not 'validation'")
            if record_b[field] != "validation":
                differences.append(f"B evaluation_split is {record_b[field]!r}, not 'validation'")

    if missing:
        return "Insufficient context", missing, differences
    if differences:
        return "Conditions differ", [], differences
    return "Same recorded conditions", [], []


def format_experiment_value(field, value):
    if value is None:
        return "Not recorded"
    if field == "features" and isinstance(value, list):
        return "[" + ", ".join(sorted(set(value))) + "]"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def signed_metric_delta(value):
    if value > 0:
        return f"+{value:.2f}"
    if value < 0:
        return f"-{abs(value):.2f}"
    return "+0.00"


def signed_setting_delta(value):
    if value > 0:
        return f"+{value:g}"
    if value < 0:
        return f"−{abs(value):g}"
    return "+0"


st.set_page_config(page_title="Dataset Explorer", page_icon="📊", layout="wide")

st.title("Dataset Explorer")
st.write("Upload a CSV file to explore its rows, columns, missing values, and duplicates.")

st.subheader("1. Upload your data")
uploaded_file = st.file_uploader(
    "Choose one CSV file",
    type=None,
    accept_multiple_files=False,
    max_upload_size=MAX_UPLOAD_SIZE_MB,
    help="Use a CSV file with a header row, saved as UTF-8. Maximum size: 5 MB.",
)

separator_label = st.radio(
    "Choose the separator used in your CSV",
    options=["Comma (,)", "Semicolon (;)"],
    horizontal=True,
)
separator = "," if separator_label.startswith("Comma") else ";"

st.info(
    "Missing-value rules: empty fields and pandas' default NA markers, such as "
    "NA, N/A, NULL, and NaN, count as missing. Other text (including spaces) "
    "is kept as text."
)

if uploaded_file is not None:
    if Path(uploaded_file.name).suffix.lower() != ".csv":
        st.error("Wrong file type. Please choose a file with the .csv extension.")
        st.stop()

    if uploaded_file.getbuffer().nbytes == 0:
        st.error("This file is empty. Choose a CSV file that contains a header row and data.")
        st.stop()

    try:
        data = pd.read_csv(
            uploaded_file,
            sep=separator,
            encoding="utf-8-sig",
            header=0,
        )
    except pd.errors.EmptyDataError:
        st.error("This file is empty or has no header row. Add a header row and try again.")
        st.stop()
    except UnicodeDecodeError:
        st.error("This file could not be read as UTF-8. Save it as UTF-8 and upload it again.")
        st.stop()
    except pd.errors.ParserError:
        st.error(
            "This CSV could not be read. Check the header, rows, and selected separator, "
            "then try again."
        )
        st.stop()
    except Exception:
        st.error(
            "This file could not be read. Check that it is a valid UTF-8 CSV with a "
            "header row, then try again."
        )
        st.stop()

    if len(data.columns) == 0:
        st.error("This CSV has no column names. Put a header row in the first line and try again.")
        st.stop()

    row_count = len(data)
    column_count = len(data.columns)
    missing_count = data.isna().sum()
    if row_count:
        missing_percent = (missing_count / row_count * 100).round(2)
    else:
        missing_percent = pd.Series(0.0, index=data.columns)
    whitespace_only_cells = data.apply(
        lambda column: column.map(
            lambda value: isinstance(value, str)
            and len(value) > 0
            and all(character == " " for character in value)
        )
    )
    whitespace_only_count = whitespace_only_cells.sum(axis=0)
    whitespace_only_row_mask = whitespace_only_cells.any(axis=1)
    whitespace_only_rows = data.loc[whitespace_only_row_mask]
    whitespace_only_total = int(whitespace_only_count.sum())
    duplicate_count = int(data.duplicated(keep="first").sum())

    st.subheader("2. Dataset summary")
    summary_row, summary_columns, summary_duplicates = st.columns(3)
    summary_row.metric("Rows", f"{row_count:,}")
    summary_columns.metric("Columns", f"{column_count:,}")
    summary_duplicates.metric("Extra exact duplicate rows", f"{duplicate_count:,}")

    if row_count == 0:
        st.info("This file has a header row but no data rows.")

    st.subheader("3. Column details")
    st.caption(
        "Whitespace-only cells contain one or more regular space characters and no other characters. "
        "Empty/NaN values, tabs, and 0 are not included. Values are counted as read and are not changed."
    )
    column_details = pd.DataFrame(
        {
            "Column name": data.columns,
            "Pandas type": [str(dtype) for dtype in data.dtypes],
            "Distinct non-missing values": data.nunique(dropna=True).to_numpy(),
            "Missing values": missing_count.to_numpy(),
            "Missing (%)": missing_percent.to_numpy(),
            "Whitespace-only cells": whitespace_only_count.to_numpy(),
        }
    )
    st.dataframe(column_details, hide_index=True, width="stretch")
    st.metric("Total whitespace-only cells", f"{whitespace_only_total:,}")

    st.subheader("4. Data preview")
    preview_count = min(row_count, 100)
    st.caption(f"Showing the first {preview_count:,} of {row_count:,} rows.")
    st.dataframe(data.head(100), hide_index=True, width="stretch")

    if st.checkbox(
        "Show only rows with cells made only of spaces",
        help="Shows every row containing at least one cell with one or more regular spaces only. "
        "This view does not change the uploaded data, summary, or chart.",
    ):
        st.caption(
            f"Showing {len(whitespace_only_rows):,} matching rows. "
            "Summary counts and chart calculations still use the full uploaded table."
        )
        st.dataframe(whitespace_only_rows, hide_index=True, width="stretch")

    st.subheader("5. Category totals")
    numeric_columns = list(data.select_dtypes(include="number").columns)

    if not numeric_columns:
        st.info(
            "The chart is unavailable because this dataset has no numeric columns. "
            "The dataset summary, column details, and preview are still available above."
        )
    else:
        non_numeric_columns = [column for column in data.columns if column not in numeric_columns]
        category_defaults = non_numeric_columns or [
            column for column in data.columns if column != numeric_columns[0]
        ]
        default_category = category_defaults[0] if category_defaults else data.columns[0]

        category_column = st.selectbox(
            "Category column",
            options=list(data.columns),
            index=list(data.columns).index(default_category),
        )
        available_numeric_columns = [
            column for column in numeric_columns if column != category_column
        ]

        if not available_numeric_columns:
            st.info(
                "The chart needs separate category and numeric columns. "
                "Choose a different category column to continue."
            )
        else:
            numeric_column = st.selectbox(
                "Numeric column to sum",
                options=available_numeric_columns,
            )
            missing_category_rows = int(data[category_column].isna().sum())
            st.caption(
                f"Rows with a missing category: {missing_category_rows:,}. "
                "These rows are excluded from category totals."
            )

            grouped_totals = data.groupby(
                category_column, dropna=True, sort=False
            )[numeric_column].sum(min_count=1)
            totals = (
                grouped_totals.rename_axis("Category")
                .reset_index(name="Total")
                .sort_values("Total", ascending=False, na_position="last", kind="stable")
            )
            numeric_totals = totals.dropna(subset=["Total"])

            st.markdown(
                f"**Aggregation:** Sum of `{numeric_column}` for each `{category_column}`, "
                f"calculated from all {row_count:,} uploaded rows. Missing numbers are "
                "ignored; groups where all numbers are missing show **No data**."
            )

            if numeric_totals.empty:
                st.info(
                    "There are no numeric values to chart for this selection. "
                    "All category totals are shown as No data in the table."
                )
            else:
                chart_totals = numeric_totals.head(20)
                if len(numeric_totals) > 20:
                    st.caption(
                        f"The chart shows only the top 20 of {len(numeric_totals):,} "
                        "categories with numeric totals, sorted from highest to lowest. "
                        "Categories marked No data remain in the table and are not plotted. "
                        "The table below includes all category totals."
                    )
                else:
                    st.caption(
                        f"The chart shows all {len(numeric_totals):,} categories with "
                        "numeric totals, sorted from highest to lowest. Categories marked "
                        "No data remain in the table and are not plotted."
                    )

                st.bar_chart(
                    chart_totals,
                    x="Category",
                    y="Total",
                    x_label=f"{category_column} (category)",
                    y_label=f"Sum of {numeric_column}",
                    sort=False,
                )

            table_totals = totals.copy()
            table_totals["Total"] = table_totals["Total"].map(
                lambda value: "No data" if pd.isna(value) else value
            )
            st.caption(
                f"Exact totals by `{category_column}` for every non-missing category value:"
            )
            st.dataframe(table_totals, hide_index=True, width="stretch")

    st.subheader("6. Inspect numeric values")
    numeric_inspection_columns = list(data.select_dtypes(include="number").columns)
    if not numeric_inspection_columns:
        st.info(
            "This dataset has no numeric columns to inspect. Numeric inspection is unavailable."
        )
    else:
        inspection_column = st.selectbox(
            "Choose a numeric column to inspect",
            options=numeric_inspection_columns,
            key="numeric_inspection_column",
        )
        numeric_series = pd.to_numeric(data[inspection_column], errors="coerce")
        numeric_array = numeric_series.to_numpy(dtype=float, na_value=np.nan)
        finite_mask = np.isfinite(numeric_array)
        values = numeric_array[finite_mask]
        usable_count = int(finite_mask.sum())
        excluded_count = row_count - usable_count
        source_row_numbers = np.arange(1, row_count + 1)

        usable_metric, excluded_metric = st.columns(2)
        usable_metric.metric("Usable finite numbers", f"{usable_count:,}")
        excluded_metric.metric("Missing or non-finite values", f"{excluded_count:,}")

        if usable_count == 0:
            st.info(
                "This column has no usable finite numbers. Missing and infinite values "
                "are excluded from the IQR calculation."
            )
        elif usable_count < 4:
            st.info(
                f"There are only {usable_count} usable finite values. At least 4 are needed "
                "for this IQR inspection, so no IQR boundaries or verdict are shown."
            )
        else:
            values_series = pd.Series(values)
            q1 = float(values_series.quantile(0.25))
            q3 = float(values_series.quantile(0.75))
            iqr = q3 - q1
            lower_boundary = q1 - 1.5 * iqr
            upper_boundary = q3 + 1.5 * iqr
            flagged_mask = finite_mask & (
                (numeric_array < lower_boundary) | (numeric_array > upper_boundary)
            )
            flagged_count = int(flagged_mask.sum())

            q1_metric, q3_metric, iqr_metric, flagged_metric = st.columns(4)
            q1_metric.metric("Q1", f"{q1:g}")
            q3_metric.metric("Q3", f"{q3:g}")
            iqr_metric.metric("IQR", f"{iqr:g}")
            flagged_metric.metric("Needs inspection", f"{flagged_count:,}")
            st.caption(
                f"IQR boundaries: {lower_boundary:g} to {upper_boundary:g}. "
                "Only values strictly below or above these boundaries are flagged. "
                "A flag means needs inspection; it does not prove a value is an error."
            )

            fig, ax = plt.subplots(figsize=(9, 2.8))
            ax.boxplot(
                values,
                orientation="horizontal",
                whis=1.5,
                showfliers=True,
                patch_artist=True,
                boxprops={"facecolor": "#dce7fa", "edgecolor": "#0757ff"},
                medianprops={"color": "#08112e", "linewidth": 2},
                flierprops={
                    "marker": "o",
                    "markerfacecolor": "#e07826",
                    "markeredgecolor": "#8b4310",
                    "markersize": 7,
                },
            )
            ax.axvline(
                lower_boundary,
                color="#0757ff",
                linestyle="--",
                label=f"Lower boundary: {lower_boundary:g}",
            )
            ax.axvline(
                upper_boundary,
                color="#a54416",
                linestyle="--",
                label=f"Upper boundary: {upper_boundary:g}",
            )
            ax.set_xlabel(inspection_column)
            ax.set_yticks([])
            ax.set_title(f"Boxplot for {inspection_column} — unusual points need inspection")
            ax.grid(axis="x", alpha=0.2)
            ax.legend(loc="best", fontsize=8)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            if flagged_count == 0:
                st.success("No values need inspection under the 1.5 × IQR rule.")
            else:
                flagged_rows = data.loc[flagged_mask].copy()
                flagged_rows.insert(
                    0,
                    "Source row",
                    source_row_numbers[flagged_mask],
                )
                st.markdown("**Rows marked “Needs inspection”**")
                st.caption(
                    "Source row is the 1-based row position in the uploaded CSV. "
                    "Original columns, including any row ID, are shown unchanged."
                )
                st.dataframe(flagged_rows, hide_index=True, width="stretch")
else:
    st.subheader("6. Inspect numeric values")
    st.info("Upload a CSV file first to inspect one of its numeric columns.")


st.subheader("7. Compare two CSV versions")
st.write(
    "Compare an older file with a newer one. This section reads text for matching and "
    "missing-cell counts; it does not change either uploaded file."
)
before_upload, after_upload = st.columns(2)
with before_upload:
    before_file = st.file_uploader(
        "BEFORE — old file",
        type=None,
        accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_SIZE_MB,
        key="comparison_before_file",
        help="CSV with a header row, UTF-8, up to 5 MB.",
    )
with after_upload:
    after_file = st.file_uploader(
        "AFTER — new file",
        type=None,
        accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_SIZE_MB,
        key="comparison_after_file",
        help="CSV with a header row, UTF-8, up to 5 MB.",
    )

if before_file is not None:
    st.caption(f"BEFORE filename: {before_file.name}")
if after_file is not None:
    st.caption(f"AFTER filename: {after_file.name}")

if before_file is None or after_file is None:
    st.info("Upload both a BEFORE file and an AFTER file to see the comparison.")
else:
    comparison_frames = {}
    comparison_files = {"BEFORE": before_file, "AFTER": after_file}
    for side, comparison_file in comparison_files.items():
        if Path(comparison_file.name).suffix.lower() != ".csv":
            st.error(f"{side}: wrong file type. Please choose a .csv file.")
            continue
        try:
            comparison_frames[side] = read_comparison_csv(comparison_file, separator)
        except pd.errors.EmptyDataError:
            st.error(f"{side}: the file is empty or has no header row.")
        except UnicodeDecodeError:
            st.error(f"{side}: the file is not valid UTF-8.")
        except pd.errors.ParserError:
            st.error(f"{side}: the CSV could not be read with the selected separator.")
        except Exception:
            st.error(f"{side}: could not read the CSV. Check its header and selected separator.")

    if len(comparison_frames) == 2:
        before_data = comparison_frames["BEFORE"]
        after_data = comparison_frames["AFTER"]
        before_missing_mask = comparison_missing_mask(before_data)
        after_missing_mask = comparison_missing_mask(after_data)
        before_missing_total = int(before_missing_mask.to_numpy().sum())
        after_missing_total = int(after_missing_mask.to_numpy().sum())

        summary_rows, summary_columns, summary_missing = st.columns(3)
        summary_rows.metric(
            "Rows",
            f"{len(before_data):,} → {len(after_data):,}",
            delta=f"Δ {len(after_data) - len(before_data):+,}",
            delta_color="off",
        )
        summary_columns.metric(
            "Columns",
            f"{len(before_data.columns):,} → {len(after_data.columns):,}",
            delta=f"Δ {len(after_data.columns) - len(before_data.columns):+,}",
            delta_color="off",
        )
        summary_missing.metric(
            "Missing cells",
            f"{before_missing_total:,} → {after_missing_total:,}",
            delta=f"Δ {after_missing_total - before_missing_total:+,}",
            delta_color="off",
        )
        st.caption(
            "Deltas are AFTER − BEFORE. For this comparison, empty cells and cells "
            "containing only whitespace are missing. Zero and literal text such as NA "
            "or null are values. IDs and other cell text, including leading zeros, "
            "are preserved as text."
        )

        before_columns = list(before_data.columns)
        after_columns = list(after_data.columns)
        before_column_set = set(before_columns)
        after_column_set = set(after_columns)
        added_columns = [column for column in after_columns if column not in before_column_set]
        removed_columns = [column for column in before_columns if column not in after_column_set]
        common_columns = [column for column in before_columns if column in after_column_set]

        with st.expander("Column changes", expanded=False):
            column_added, column_removed = st.columns(2)
            with column_added:
                st.markdown("**Added columns**")
                if added_columns:
                    st.success("Added — " + ", ".join(added_columns))
                else:
                    st.info("Added — no columns")
            with column_removed:
                st.markdown("**Removed columns**")
                if removed_columns:
                    st.error("Removed — " + ", ".join(removed_columns))
                else:
                    st.info("Removed — no columns")

        with st.expander("Missing cells in common columns", expanded=False):
            if common_columns:
                before_common_missing = before_missing_mask[common_columns].sum()
                after_common_missing = after_missing_mask[common_columns].sum()
                missing_by_column = pd.DataFrame(
                    {
                        "Column": common_columns,
                        "BEFORE missing": [int(before_common_missing[column]) for column in common_columns],
                        "AFTER missing": [int(after_common_missing[column]) for column in common_columns],
                    }
                )
                st.dataframe(missing_by_column, hide_index=True, width="stretch")
            else:
                st.info("There are no common columns to compare.")

        with st.expander("Record changes by ID", expanded=False):
            if not common_columns:
                st.info("Record matching is unavailable because the files have no common columns.")
            else:
                selected_id = st.selectbox(
                    "Choose a common ID column",
                    options=common_columns,
                    index=None,
                    placeholder="Select a column...",
                    key="comparison_id_column",
                    help="An ID should identify the same record in both files.",
                )
                if selected_id is None:
                    st.info("Record matching is unavailable until you select a common ID column.")
                else:
                    before_ids = before_data[selected_id]
                    after_ids = after_data[selected_id]
                    before_blank = before_ids.map(is_comparison_missing)
                    after_blank = after_ids.map(is_comparison_missing)
                    before_duplicate = (~before_blank) & before_ids.duplicated(keep=False)
                    after_duplicate = (~after_blank) & after_ids.duplicated(keep=False)
                    id_problems = []
                    if before_blank.any():
                        id_problems.append(
                            f"BEFORE has {int(before_blank.sum()):,} blank ID value(s)."
                        )
                    if after_blank.any():
                        id_problems.append(
                            f"AFTER has {int(after_blank.sum()):,} blank ID value(s)."
                        )
                    if before_duplicate.any():
                        id_problems.append(
                            f"BEFORE has {int(before_duplicate.sum()):,} row(s) with duplicate IDs."
                        )
                    if after_duplicate.any():
                        id_problems.append(
                            f"AFTER has {int(after_duplicate.sum()):,} row(s) with duplicate IDs."
                        )

                    if id_problems:
                        st.warning(
                            "Record matching is unavailable because the selected ID must be "
                            "nonblank and unique in both files. " + " ".join(id_problems)
                        )
                    else:
                        before_id_values = before_ids.tolist()
                        after_id_values = after_ids.tolist()
                        before_id_set = set(before_id_values)
                        after_id_set = set(after_id_values)
                        added_ids = [value for value in after_id_values if value not in before_id_set]
                        removed_ids = [value for value in before_id_values if value not in after_id_set]
                        common_ids = [value for value in before_id_values if value in after_id_set]
                        before_by_id = before_data.set_index(selected_id, drop=False)
                        after_by_id = after_data.set_index(selected_id, drop=False)
                        common_value_columns = [
                            column for column in common_columns if column != selected_id
                        ]
                        changed_ids = []
                        unchanged_ids = []
                        for record_id in common_ids:
                            changed = any(
                                comparison_value(before_by_id.at[record_id, column])
                                != comparison_value(after_by_id.at[record_id, column])
                                for column in common_value_columns
                            )
                            (changed_ids if changed else unchanged_ids).append(record_id)

                        st.caption(
                            "ID values are matched exactly as text. Changed/Unchanged compare "
                            "common non-ID columns; added or removed columns are listed separately."
                        )
                        added_label, removed_label = st.columns(2)
                        with added_label:
                            if added_ids:
                                st.success(f"Added — {len(added_ids):,}: " + ", ".join(added_ids))
                            else:
                                st.info("Added — 0 records")
                        with removed_label:
                            if removed_ids:
                                st.error(f"Removed — {len(removed_ids):,}: " + ", ".join(removed_ids))
                            else:
                                st.info("Removed — 0 records")

                        if changed_ids:
                            st.warning(
                                f"Changed — {len(changed_ids):,}: " + ", ".join(changed_ids)
                            )
                        else:
                            st.info("Changed — 0 records")
                        st.markdown(
                            f"Unchanged — {len(unchanged_ids):,}: "
                            + (", ".join(unchanged_ids) if unchanged_ids else "none")
                        )

                        if added_ids:
                            st.markdown("**Added original records (from AFTER)**")
                            st.dataframe(
                                after_data.loc[after_ids.isin(added_ids)],
                                hide_index=True,
                                width="stretch",
                            )
                        else:
                            st.caption("No added records.")
                        if removed_ids:
                            st.markdown("**Removed original records (from BEFORE)**")
                            st.dataframe(
                                before_data.loc[before_ids.isin(removed_ids)],
                                hide_index=True,
                                width="stretch",
                            )
                        else:
                            st.caption("No removed records.")


st.subheader("8. Compare experiment summaries")
st.write(
    "Compare two saved experiment summary JSON files. These records describe the "
    "experiment; this view does not train or load a model."
)
experiment_upload_a, experiment_upload_b = st.columns(2)
with experiment_upload_a:
    experiment_file_a = st.file_uploader(
        "Experiment A",
        type=["json"],
        accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_SIZE_MB,
        key="experiment_summary_a",
    )
with experiment_upload_b:
    experiment_file_b = st.file_uploader(
        "Experiment B",
        type=["json"],
        accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_SIZE_MB,
        key="experiment_summary_b",
    )

if experiment_file_a is not None:
    st.caption(f"A filename: {experiment_file_a.name}")
if experiment_file_b is not None:
    st.caption(f"B filename: {experiment_file_b.name}")

if experiment_file_a is None or experiment_file_b is None:
    st.info("Upload one JSON summary as A and one as B to compare experiments.")
else:
    experiment_records = {}
    experiment_files = {"A": experiment_file_a, "B": experiment_file_b}
    for side, experiment_file in experiment_files.items():
        try:
            experiment_records[side] = read_experiment_json(experiment_file)
        except ValueError as error:
            st.error(f"{side} ({experiment_file.name}): {error}")

    if len(experiment_records) == 2:
        record_a = experiment_records["A"]
        record_b = experiment_records["B"]
        run_id_a = format_experiment_value("run_id", record_a.get("run_id"))
        run_id_b = format_experiment_value("run_id", record_b.get("run_id"))
        st.caption(f"A run ID: {run_id_a} · B run ID: {run_id_b}")

        status, missing_context, context_differences = experiment_context_status(
            record_a, record_b
        )
        metric_values = {"A": {}, "B": {}}
        metric_states = {"A": {}, "B": {}}
        invalid_metric_messages = []
        missing_primary_metrics = []
        metric_names = ("train_f1", "f1", "precision", "recall")

        for side, record in experiment_records.items():
            metric_record = record.get("metrics")
            if not isinstance(metric_record, dict):
                metric_record = {}
                for metric_name in metric_names:
                    metric_values[side][metric_name] = None
                    metric_states[side][metric_name] = "missing"
                    if metric_name in {"f1", "precision", "recall"}:
                        missing_primary_metrics.append(f"{side}.metrics.{metric_name}")
            else:
                for metric_name in metric_names:
                    if metric_name not in metric_record:
                        metric_values[side][metric_name] = None
                        metric_states[side][metric_name] = "missing"
                        if metric_name in {"f1", "precision", "recall"}:
                            missing_primary_metrics.append(f"{side}.metrics.{metric_name}")
                    elif not is_finite_metric(metric_record[metric_name]):
                        metric_values[side][metric_name] = None
                        metric_states[side][metric_name] = "invalid"
                        invalid_metric_messages.append(
                            f"{side}.metrics.{metric_name} must be a finite number in [0, 1]."
                        )
                    else:
                        metric_values[side][metric_name] = float(metric_record[metric_name])
                        metric_states[side][metric_name] = "valid"

        if missing_primary_metrics:
            status = "Insufficient context"
            missing_context.extend(
                f"Missing metric: {field}" for field in missing_primary_metrics
            )

        st.markdown(f"**Comparison status: {status}**")
        if status == "Same recorded conditions":
            st.caption(
                "Required recorded conditions match. This does not verify the underlying "
                "data rows, the measurements, or their quality. Model, penalty, and C are "
                "settings to inspect; their differences alone do not change this status."
            )
        elif status == "Conditions differ":
            st.info("Recorded conditions do not match the required validation comparison.")
        else:
            st.info("Some required context is missing or not recorded; no defaults were assumed.")
        for field in missing_context:
            st.caption(f"Missing or unknown: {field}")
        for difference in context_differences:
            st.caption(f"Condition difference: {difference}")

        if invalid_metric_messages:
            st.error(
                "Invalid metric values were found. Calculations using those values are withheld: "
                + " ".join(invalid_metric_messages)
            )

        metric_cards = st.columns(3)
        for card, metric_name, label in zip(
            metric_cards,
            ("f1", "precision", "recall"),
            ("F1", "Precision", "Recall"),
        ):
            state_a = metric_states["A"][metric_name]
            state_b = metric_states["B"][metric_name]
            value_a = metric_values["A"][metric_name]
            value_b = metric_values["B"][metric_name]
            shown_a = f"{value_a:.2f}" if state_a == "valid" else state_a.title()
            shown_b = f"{value_b:.2f}" if state_b == "valid" else state_b.title()
            metric_delta = None
            if state_a == "valid" and state_b == "valid":
                metric_delta = signed_metric_delta(value_b - value_a)
            card.metric(
                label,
                f"{shown_a} → {shown_b}",
                delta=metric_delta,
                delta_color="normal",
            )
        st.caption(
            "Metric deltas are B − A. Green, red, and neutral directions describe the "
            "numeric change only; they do not select a winner or establish better quality."
        )

        setting_fields = (
            ("run_id", "Run ID"),
            ("dataset_id", "Dataset ID"),
            ("split_id", "Split ID"),
            ("target", "Target"),
            ("positive_class", "Positive class"),
            ("features", "Features"),
            ("evaluation_split", "Evaluation split"),
            ("threshold", "Threshold"),
            ("seed", "Seed"),
            ("model", "Model"),
            ("penalty", "Penalty"),
            ("C", "C"),
        )

        with st.expander("Recorded settings and differences", expanded=False):
            setting_rows = []
            for field, label in setting_fields:
                value_a = record_a.get(field)
                value_b = record_b.get(field)
                shown_a = format_experiment_value(field, value_a)
                shown_b = format_experiment_value(field, value_b)
                known_a = field in record_a and value_a is not None
                known_b = field in record_b and value_b is not None
                if not known_a or not known_b:
                    difference = "Not recorded"
                elif normalized_experiment_context(field, value_a) == normalized_experiment_context(
                    field, value_b
                ):
                    difference = "Same"
                elif (
                    field == "C"
                    and is_finite_number(value_a)
                    and is_finite_number(value_b)
                ):
                    difference = "Δ " + signed_setting_delta(value_b - value_a)
                else:
                    difference = "Different"
                setting_rows.append(
                    {"Setting": label, "A": shown_a, "B": shown_b, "Difference": difference}
                )
            st.dataframe(pd.DataFrame(setting_rows), hide_index=True, width="stretch")
            notes = []
            if record_a.get("note"):
                notes.append(f"A note: {record_a['note']}")
            if record_b.get("note"):
                notes.append(f"B note: {record_b['note']}")
            if notes:
                for note in notes:
                    st.caption(str(note))

        def validation_gap(record, side):
            if record.get("evaluation_split") != "validation":
                split = format_experiment_value("evaluation_split", record.get("evaluation_split"))
                return f"Unavailable: evaluation_split is {split}"
            train_state = metric_states[side]["train_f1"]
            f1_state = metric_states[side]["f1"]
            if train_state == "valid" and f1_state == "valid":
                return f"{metric_values[side]['train_f1'] - metric_values[side]['f1']:.2f}"
            if train_state == "invalid" or f1_state == "invalid":
                return "Unavailable: invalid metric"
            return "Unavailable: metric not recorded"

        with st.expander("Train − validation F1 details", expanded=False):
            gap_rows = []
            for side, record in (("A", record_a), ("B", record_b)):
                gap_rows.append(
                    {
                        "Run": side,
                        "Evaluation split": format_experiment_value(
                            "evaluation_split", record.get("evaluation_split")
                        ),
                        "Train F1": (
                            f"{metric_values[side]['train_f1']:.2f}"
                            if metric_states[side]["train_f1"] == "valid"
                            else metric_states[side]["train_f1"].title()
                        ),
                        "F1 on recorded split": (
                            f"{metric_values[side]['f1']:.2f}"
                            if metric_states[side]["f1"] == "valid"
                            else metric_states[side]["f1"].title()
                        ),
                        "Train − validation F1": validation_gap(record, side),
                    }
                )
            st.dataframe(pd.DataFrame(gap_rows), hide_index=True, width="stretch")
            st.caption(
                "The gap is calculated only when that run records evaluation_split as validation. "
                "No train-to-validation gap is inferred for other or missing splits."
            )

        st.caption(
            "Run IDs and split IDs are recorded labels, not audited hashes. Matching labels "
            "cannot prove that the underlying rows or measurements are identical."
        )
