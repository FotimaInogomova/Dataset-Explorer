# Dataset Explorer M3C6 release receipt

Archive: `Dataset_Explorer_FotimaInogomova_v2.zip`
Date: 2026-11-11 (Asia/Tashkent)
Package type: portable Python source package; not an installer or executable

## Actual results

| Check | Status | Result |
|---|---|---|
| Archive layout and integrity | PASS | ZIP integrity test passed. It contains one `Dataset_Explorer/` root and 11 files. `.venv`, `.git`, caches, private data, and absolute machine paths are excluded. macOS/Linux start scripts have Unix mode 755. |
| Windows launcher and startup | PASS | Extracted this exact ZIP to a new temporary folder and ran `START_WINDOWS.cmd --no-browser`. It selected Python 3.12.6, created the package-local `.venv`, installed the pinned app requirements, and started Streamlit. |
| Package imports and versions | PASS | Python 3.12.6; Streamlit 1.66.0; pandas 3.0.6; NumPy 2.5.4; Matplotlib 3.11.2. Import command: `import streamlit, pandas, numpy, matplotlib`. All imports succeeded. |
| Local server health | PASS | `http://127.0.0.1:8501/_stcore/health` returned HTTP 200 with body `ok`. |
| Normal sample upload | PASS | `samples/M3C6_SAMPLE.csv` loaded in the extracted app. The summary showed 3 rows and 3 columns. The table showed category totals A=10, B=20, C=30. |
| Empty sample upload | PASS | The 0-byte `samples/M3C6_EMPTY.csv` produced: “This file is empty. Choose a CSV file that contains a header row and data.” No traceback appeared. |
| Recovery after empty file | PASS | Re-uploaded the valid sample after the empty-file message; the 3-row, 3-column summary returned. |
| macOS launcher | NOT RUN | Not tested on macOS. |
| Linux launcher | NOT RUN | Not tested on Linux. |
| Peer verification | NOT RUN | Only a self-check was performed. |
| Python 3.13 fallback | BLOCKED on this computer | The first Windows launcher draft selected Python 3.13.2; its `ensurepip` failed because the bundled pip wheel could not be found. No global Python installation was changed. The final Windows launcher now prefers the working, tested Python 3.12.6. |

The test server was stopped with Ctrl+C after the checks. The extracted temporary test folder was kept separate from the original project. The ZIP was not changed after these checks. This receipt is stored beside the ZIP and is not inside it.
