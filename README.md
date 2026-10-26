# Dataset Explorer

Dataset Explorer is a small Streamlit app for viewing a CSV file. It reports the dataset size, column types, distinct non-missing values, missing values, and extra exact duplicate rows. It can also show the sum of a numeric column for each category in a bar chart and totals table. It does not change or clean the source data.

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

The file must use UTF-8 encoding. Empty fields and pandas' default missing-value markers (such as `NA`, `N/A`, `NULL`, and `NaN`) count as missing. Other text is kept as text. Counts and duplicate checks use the full uploaded file, not just the preview. Duplicate counts exclude the first occurrence of each exact row.

For the category chart, missing category rows are counted separately and excluded from category totals. Missing numeric values are ignored by the sum; a category with no numeric values is labeled `No data` in the table, not treated as zero. The chart plots only categories with numeric totals, sorted from highest to lowest, and shows at most 20. The totals table includes every non-missing category.

## Dependencies

The project virtual environment already contains the pinned dependencies. To
reinstall them into it, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Verification

See `checks.txt` for the checks run, their actual results, and items that still
need a manual browser check.
