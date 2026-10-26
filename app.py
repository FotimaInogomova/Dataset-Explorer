from pathlib import Path

import pandas as pd
import streamlit as st


MAX_UPLOAD_SIZE_MB = 5

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
    duplicate_count = int(data.duplicated(keep="first").sum())

    st.subheader("2. Dataset summary")
    summary_row, summary_columns, summary_duplicates = st.columns(3)
    summary_row.metric("Rows", f"{row_count:,}")
    summary_columns.metric("Columns", f"{column_count:,}")
    summary_duplicates.metric("Extra exact duplicate rows", f"{duplicate_count:,}")

    if row_count == 0:
        st.info("This file has a header row but no data rows.")

    st.subheader("3. Column details")
    column_details = pd.DataFrame(
        {
            "Column name": data.columns,
            "Pandas type": [str(dtype) for dtype in data.dtypes],
            "Distinct non-missing values": data.nunique(dropna=True).to_numpy(),
            "Missing values": missing_count.to_numpy(),
            "Missing (%)": missing_percent.to_numpy(),
        }
    )
    st.dataframe(column_details, hide_index=True, width="stretch")

    st.subheader("4. Data preview")
    preview_count = min(row_count, 100)
    st.caption(f"Showing the first {preview_count:,} of {row_count:,} rows.")
    st.dataframe(data.head(100), hide_index=True, width="stretch")

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
