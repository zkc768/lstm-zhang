# lst_models_google_drive_raw_data_guide

Status: draft technical guide.

Scope: `lst_models` V2 notebooks and data access only. This document defines
how new Colab notebooks locate raw stock data, convert the raw 1-minute `.txt`
files to 5-minute bars, and organize Drive outputs. It does not authorize
holdout/test contact and does not duplicate raw data.

## 1. Authoritative Raw Source

The raw stock files remain in the existing Google Drive folder:

```text
folder name: s&p 100 adjusted 1 min data
folder id:   154SlcH3nViUcvPXFBM-E4NPg_ybljBTG
folder URL:  https://drive.google.com/drive/folders/154SlcH3nViUcvPXFBM-E4NPg_ybljBTG
```

Required files:

| ticker | file name | file id |
|---|---|---|
| CSCO | `CSCO.txt` | `17A49kUiMELuQqdkOhw1KrpudjP5i5xIN` |
| JPM | `JPM.txt` | `11UQUJKVXTrBb8XFWY5Z8JDQ8_4i_DE-q` |
| KO | `KO.txt` | `1XmtwuZ2dTP20NsU27w5dMyRdSvdnNTSn` |
| MSFT | `MSFT.txt` | `1Ud1SQpQbaiRKemFf9dgu1o_raUPnFvGs` |
| WMT | `WMT.txt` | `1NNfsoUJrrsj2ae5EnC-PTPcZs_QGR_7c` |

The machine-readable manifest is:

```text
configs/lst_models_data.yaml
```

New notebooks should read this manifest or copy its values exactly. They must
not find raw data by scanning mounted Drive folders, shortcuts, or old project
folders.

## 2. Notebook Data Access Rule

Default notebook behavior:

```text
Google Drive API file ID -> /content/lst_models_raw_stock_data/<ticker>.txt
```

Rules:

- Do not mount MyDrive in the default setup cell.
- Do not use `/content/drive/MyDrive/stockdata` as the active raw source.
- Do not rely on Drive shortcuts such as `Dow_30_1min`.
- Do not copy raw files into the project folder as a second source of truth.
- Fail loudly with the exact missing ticker file or file ID.
- Download raw `.txt` files into the Colab runtime first, then process locally.

A notebook may have an optional backup cell that writes results to Drive, but
raw-data access and result backup are separate concerns.

## 3. Raw `.txt` Format

Expected raw `.txt` columns:

```text
Date, Time, Open, High, Low, Close, Volume
```

Expected parsing:

```text
date_format = %m/%d/%Y
time_format = %H:%M
```

A header row may be present. The loader must handle the documented schema only;
if a file has unexpected columns, the notebook or package loader must raise a
clear schema error rather than silently guessing.

## 4. Canonical 1min To 5min Recipe

Every V2 notebook that needs bar data must use this recipe exactly:

```yaml
input_frequency: 1min
output_frequency: 5min
resample_rule: 5min
market_open: "09:30"
market_close: "16:00"
agg:
  open: first
  high: max
  low: min
  close: last
  volume: sum
drop_na_subset: [open, high, low, close, volume]
output_columns: [ticker, timestamp, open, high, low, close, volume]
```

Apply the regular trading hours filter to both the 1-minute rows and the
resampled 5-minute rows. Sort by `(ticker, timestamp)` before downstream split,
label, feature, and window construction.

## 5. Holdout/Test Boundary

Validation-only notebooks must preserve:

```text
val_end = 2017-01-25
holdout_test_contact = false
```

Bars at or after `val_end` belong to the closed holdout/test partition. In
validation-only work, they must not be read, transformed, windowed, scored,
summarized, or used for wording decisions.

## 6. Drive Project Folder

The cloud project folder is:

```text
My Drive/lst_models/
```

Recommended subfolders:

```text
lst_models/
├── notebooks/
├── data/
│   ├── raw_manifest/
│   └── five_minute_runtime/
├── configs/
├── docs/
│   └── protocols/
├── results/
└── artifacts/
```

`data/raw_manifest/` is for manifests and README files only. It should not
become a duplicate raw data store unless the user explicitly approves a raw-data
copy task.

## 7. Minimal Colab Pattern

```python
from pathlib import Path

RAW_DATA_DIR = Path("/content/lst_models_raw_stock_data")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_DRIVE_FILES = {
    "CSCO": {"name": "CSCO.txt", "file_id": "17A49kUiMELuQqdkOhw1KrpudjP5i5xIN"},
    "JPM": {"name": "JPM.txt", "file_id": "11UQUJKVXTrBb8XFWY5Z8JDQ8_4i_DE-q"},
    "KO": {"name": "KO.txt", "file_id": "1XmtwuZ2dTP20NsU27w5dMyRdSvdnNTSn"},
    "MSFT": {"name": "MSFT.txt", "file_id": "1Ud1SQpQbaiRKemFf9dgu1o_raUPnFvGs"},
    "WMT": {"name": "WMT.txt", "file_id": "1NNfsoUJrrsj2ae5EnC-PTPcZs_QGR_7c"},
}

# Download by file ID through the Colab Drive API, then parse/resample locally.
# Do not scan mounted folders to discover raw data.
```

The actual downloader may live in package code later, but its behavior must
match `configs/lst_models_data.yaml`.
