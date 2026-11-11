# Dataset Explorer

Dataset Explorer is a small Streamlit app for inspecting and comparing CSV files. For one dataset, it reports the row and column counts, column types, distinct non-missing values, missing values, whitespace-only cells, and extra exact duplicate rows. It can show category sums in a bar chart, inspect numeric values with an IQR boxplot, and optionally show rows containing spaces only. It can also compare an older and a newer CSV by schema, missing cells, and record ID. It does not change or clean the source data.

## Verified environment

This project was verified on Windows 11 Home (64-bit) with Python 3.12.6. The
packages used by the project are pinned in `requirements.txt`; the verified
versions are pandas 3.0.6, NumPy 2.5.4, Matplotlib 3.11.2, scikit-learn 1.9.1,
and Streamlit 1.66.0.

## Run the app

Open a terminal in this project folder and run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open the local URL printed in the terminal (usually
http://localhost:8501). To stop the app, press Ctrl+C in that terminal.

## Use the app

1. Choose one `.csv` file up to 5 MB.
2. The first row is read as the column header.
3. Choose comma or semicolon to match the separator in your file.
4. Review the summary, column details, and preview of up to the first 100 rows.
5. Choose a category column and a numeric column to see category totals. The chart shows at most the top 20 categories; the table shows every category total.
6. In **Inspect numeric values**, choose a numeric column to see its finite-value count, missing/excluded count, boxplot, IQR boundaries, and rows that need inspection. At least four finite values are needed for an IQR verdict. A flag asks you to inspect a value; it does not mean the value is wrong.
7. In **Compare two CSV versions**, upload the older file as BEFORE and the newer file as AFTER. Review the row, column, and missing-cell totals, then expand the details. Record matching requires a shared ID that is nonblank and unique in both files.
8. In **Compare experiment summaries**, upload two `format_version: 1` JSON summaries as A and B. The section compares F1, precision, and recall, shows recorded settings, and checks whether the recorded validation conditions match. It does not declare a winner or verify the underlying data.

The file must use UTF-8 encoding. Empty fields and pandas' default missing-value markers (such as `NA`, `N/A`, `NULL`, and `NaN`) count as missing. Other text is kept as text. Counts and duplicate checks use the full uploaded file, not just the preview. Duplicate counts exclude the first occurrence of each exact row.

The comparison section reads cell text as text so IDs such as `001` remain distinct from `1`. In that section, empty and whitespace-only cells count as missing, while `0` and literal strings such as `NA` and `null` remain values. Added and removed records are matched by exact ID text, never by row position or by the net row-count change. Comparison summaries use every row; detailed changes are in collapsed sections.

Experiment JSON metrics must be finite numbers from 0 through 1. A zero is valid. Metric direction is shown as a numerical change, not as a quality judgment. A train-to-validation F1 gap is shown only when the record says `evaluation_split: "validation"`; otherwise the gap is unavailable. The example records are synthetic practice data, not model exports or measured results.

For the category chart, missing category rows are counted separately and excluded from category totals. Missing numeric values are ignored by the sum; a category with no numeric values is labeled `No data` in the table, not treated as zero. The chart plots only categories with numeric totals, sorted from highest to lowest, and shows at most 20. The totals table includes every non-missing category.

## Dependencies

The project virtual environment already contains the pinned dependencies. To
reinstall them into it, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Verification

The comparison was checked with the M3C4 sample pair: BEFORE has 6 rows and 3
missing cells; AFTER has 7 rows and 1 missing cell. Matching by `row_id` finds
G/H/I as added and E/F as removed. Same-file, swapped-file, reordered-row,
duplicate-ID, and text-ID checks were also run.

On Windows, `start_dataset_explorer.ps1` starts the app with the project `.venv` and opens its local page. A desktop shortcut can point to this script.
