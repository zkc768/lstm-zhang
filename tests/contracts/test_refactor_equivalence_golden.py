"""Golden equivalence tests for the provenance-hashed rebuild mechanism.

Phase G of `docs/lst_models_post_stage02_code_migration_plan.md` (Route A).

Contract:

- The GOLDEN constants below were captured from the pre-migration Stage 01 /
  data.py code on 2026-06-09, before any code movement.
- NEVER edit a GOLDEN constant to make a refactor pass. A mismatch means the
  refactor changed rebuild behavior; fix the code. A deliberate mechanism
  change is out of migration scope and needs explicit user approval plus
  protocol updates.
- Phase 2 (2026-06-09) switched the imports below from stage01 privates to
  the public domain modules (data.py, splits.py, features.py, windows.py)
  without changing any GOLDEN constant. This file is now a permanent
  regression guard on the provenance payload functions. The alias-identity
  test remains transitional until migration Phase 4.
- `feature_rebuild_code_sha256` itself is intentionally NOT pinned here: it
  hashes source text and is expected to change when functions move. The
  data-level outputs pinned below are the equivalence gate (migration plan
  section 5).
- Constants are pinned to the project environment
  (`E:\\codex_workspace\\_envs\\py311_shared`). If that environment's
  pandas/numpy versions change and alter serialization, re-capture requires
  explicit user approval, recorded in the migration notes.

Re-capture / inspection: `python tests/contracts/test_refactor_equivalence_golden.py`
prints the currently computed values as JSON.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.data import (  # noqa: E402
    load_sample_event_index,
    load_train_bars,
    read_raw_txt_file,
    resample_1min_to_5min,
)
from lst_models.features import build_feature_frame, require_feature_columns  # noqa: E402
from lst_models.splits import build_train_inner_folds, train_valid_events  # noqa: E402
from lst_models.windows import (  # noqa: E402
    build_window_dataset,
    cap_indices,
    fold_indices,
    materialize_window_matrix,
    sample_id_hash,
)

import pytest  # noqa: E402


TICKERS = ["GA", "GB"]
TRAIN_DAYS = ["2022-03-01", "2022-03-02", "2022-03-03"]
MINUTES_PER_DAY = 210  # 09:30 to 12:59 -> 42 five-minute bars per day
WINDOW_SIZE = 5
FEATURE_COLUMNS = ("log_return", "rolling_volatility_20", "time_of_day_sin")

GOLDEN = {
    "raw_one_minute_sha256": "a2d6dadeeb56e740bacc7e88853a0cf276ceaf3fef1546edb6e723439dcbf177",
    "five_minute_sha256": "1ca805c7eb26af308341c897f59f634d8447eb081442cb2a7c31498ed0029c0c",
    "train_bars_sha256": "b0c0a7992015ac308cc79b077e61bb05bb034f7f4b92e0c5ee7db8d0fa255002",
    "sample_event_index_sha256": "4a066904c88d3a7b425763bf6e091dbf6c0391d682dd3022c3e3fe2beb901632",
    "train_valid_events_sha256": "ae6ec1713e9a54fdf8218039e4ee35621e2472918e9651789f4224df6cdc90c9",
    "fold_manifest_sha256": "fb9bd9267d0911e56d09f0e3aff9569f1e35803f8494ee4595e3acf8b0b4ce95",
    "feature_frame_sha256": "6fb1430bdc898ae76718a1351494c1e6929d9ad9c0fd27bda5013f648f19dcb9",
    "feature_added_columns": [
        "log_return",
        "close_to_open_return",
        "high_low_range",
        "rolling_volatility_20",
        "rsi_14",
        "bollinger_pctb",
        "normalized_macd_hist",
        "normalized_volume_20",
        "time_of_day_sin",
        "time_of_day_cos",
    ],
    "window_metadata_sha256": "5a053f9ffe120ef47c986dd984a47ed4f9dd2000922868b104266196ab5a9140",
    "window_matrix_sha256": "34224613f4f039d9ee43a896b66a0bbda0c3786fde4c1daaacca22518a63380f",
    "window_matrix_shape": [186, 15],
    "window_matrix_dtype": "float32",
    "fold0_train_indices_sha256": "7d1ac43f6b5fa45ded60eb496eb24096d40f746e83aabbeb5b30bddd4627a342",
    "fold0_train_count": 62,
    "fold0_eval_indices_sha256": "171ea41ba0f7f2b78c05d74585fe52eacd5c4d92d5568664f4a7c1455359a86f",
    "fold0_eval_count": 62,
    "capped_fold0_train_indices": [0, 1, 29, 30, 93, 95, 122, 123],
    "sample_id_hash_basic": "194591a924f6704e7c665d249d97f493ee087c22fc4f07ec32701e2f6d8a6e4e",
    "sample_id_hash_empty": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


def _frame_sha256(frame: pd.DataFrame) -> str:
    text = frame.to_csv(index=False, float_format="%.10g", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _indices_sha256(indices: np.ndarray) -> str:
    text = ",".join(str(int(value)) for value in indices)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _one_minute_rows(ticker_index: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    base = 50.0 + 5.0 * ticker_index
    for day_index, day in enumerate(TRAIN_DAYS):
        start = pd.Timestamp(f"{day} 09:30")
        for minute in range(MINUTES_PER_DAY):
            ts = start + pd.Timedelta(minutes=minute)
            wave = np.sin(0.31 * minute + 0.7 * day_index + ticker_index)
            close = base + 0.8 * wave + 0.3 * day_index + 0.002 * minute
            rows.append(
                {
                    "Date": ts.strftime("%m/%d/%Y"),
                    "Time": ts.strftime("%H:%M"),
                    "Open": round(close - 0.01, 6),
                    "High": round(close + 0.02, 6),
                    "Low": round(close - 0.02, 6),
                    "Close": round(close, 6),
                    "Volume": 500 + 13 * (minute % 7) + ticker_index,
                }
            )
    return rows


def _raw_config() -> dict[str, object]:
    return {
        "txt_columns": ["Date", "Time", "Open", "High", "Low", "Close", "Volume"],
        "date_format": "%m/%d/%Y",
        "time_format": "%H:%M",
    }


def _five_minute_recipe() -> dict[str, object]:
    return {
        "market_open": "09:30",
        "market_close": "16:00",
        "resample_rule": "5min",
        "agg": {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        },
        "drop_na_subset": ["open", "high", "low", "close", "volume"],
        "output_columns": [
            "ticker",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
    }


def _write_raw_files(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for ticker_index, ticker in enumerate(TICKERS):
        frame = pd.DataFrame(_one_minute_rows(ticker_index))
        frame.to_csv(raw_dir / f"{ticker}.txt", index=False)


def _raw_manifest(raw_dir: Path) -> dict[str, object]:
    return {
        "tickers": TICKERS,
        "raw_source": {
            "local_download_dir": str(raw_dir),
            "files": {ticker: {"name": f"{ticker}.txt"} for ticker in TICKERS},
            **_raw_config(),
        },
        "five_minute_recipe": _five_minute_recipe(),
    }


def _split_freeze() -> dict[str, str]:
    return {
        "train_start": "2022-03-01 00:00:00",
        "train_end": "2022-03-04 00:00:00",
        "validation_start": "2022-03-04 00:00:00",
        "validation_end": "2022-03-05 00:00:00",
        "closed_holdout_test_start": "2022-03-05 00:00:00",
    }


def _load_bars(raw_dir: Path) -> pd.DataFrame:
    _write_raw_files(raw_dir)
    return load_train_bars(
        _raw_manifest(raw_dir), _split_freeze(), {"raw_data_dir": str(raw_dir)}
    )


def _sample_events_frame(bars: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for position, record in enumerate(
        bars.sort_values(["ticker", "timestamp"]).to_dict(orient="records")
    ):
        ts = pd.Timestamp(record["timestamp"])
        rows.append(
            {
                "sample_id": f"{record['ticker']}_{ts:%Y%m%d_%H%M}",
                "ticker": record["ticker"],
                "target_timestamp": ts.isoformat(),
                "trading_day": str(record["trading_day"]),
                "split": "train",
                "label": (position + ts.day) % 2,
                "valid_label": position % 17 != 0,
            }
        )
    return pd.DataFrame(rows)


def _window_dataset(bars: pd.DataFrame, train_events: pd.DataFrame):
    feature_frame = build_feature_frame(bars)
    require_feature_columns(FEATURE_COLUMNS, feature_frame)
    return build_window_dataset(
        feature_frame,
        train_events,
        feature_set="golden_set",
        feature_columns=FEATURE_COLUMNS,
        window_size=WINDOW_SIZE,
    )


def _pipeline(tmp_dir: Path) -> dict[str, object]:
    raw_dir = tmp_dir / "raw"
    one_minute = []
    _write_raw_files(raw_dir)
    for ticker_index, ticker in enumerate(TICKERS):
        one_minute.append(
            read_raw_txt_file(raw_dir / f"{ticker}.txt", ticker, _raw_config())
        )
    one_minute_frame = pd.concat(one_minute, ignore_index=True)
    five_minute_frame = resample_1min_to_5min(one_minute_frame, _five_minute_recipe())

    bars = _load_bars(raw_dir)
    events_path = tmp_dir / "sample_event_index.csv"
    _sample_events_frame(bars).to_csv(events_path, index=False)
    sample_events = load_sample_event_index(events_path)
    train_events = train_valid_events(sample_events)
    folds = build_train_inner_folds(train_events, 2)

    feature_frame = build_feature_frame(bars)
    dataset = _window_dataset(bars, train_events)
    all_indices = np.arange(len(dataset.metadata), dtype=int)
    matrix = materialize_window_matrix(dataset, all_indices)

    fold0 = folds.iloc[0].to_dict()
    train_idx, eval_idx = fold_indices(dataset.metadata, fold0)
    capped = cap_indices(dataset.metadata, train_idx, 10)

    metadata_text_frame = dataset.metadata.copy()
    metadata_text_frame["target_timestamp"] = metadata_text_frame[
        "target_timestamp"
    ].map(lambda value: pd.Timestamp(value).isoformat())

    return {
        "raw_one_minute_sha256": _frame_sha256(one_minute_frame),
        "five_minute_sha256": _frame_sha256(five_minute_frame),
        "train_bars_sha256": _frame_sha256(bars),
        "sample_event_index_sha256": _frame_sha256(sample_events),
        "train_valid_events_sha256": _frame_sha256(train_events),
        "fold_manifest_sha256": _frame_sha256(folds),
        "feature_frame_sha256": _frame_sha256(feature_frame),
        "feature_added_columns": [
            column for column in feature_frame.columns if column not in bars.columns
        ],
        "window_metadata_sha256": _frame_sha256(metadata_text_frame),
        "window_matrix_sha256": hashlib.sha256(matrix.tobytes()).hexdigest(),
        "window_matrix_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "window_matrix_dtype": str(matrix.dtype),
        "fold0_train_indices_sha256": _indices_sha256(train_idx),
        "fold0_train_count": int(len(train_idx)),
        "fold0_eval_indices_sha256": _indices_sha256(eval_idx),
        "fold0_eval_count": int(len(eval_idx)),
        "capped_fold0_train_indices": [int(value) for value in capped],
        "sample_id_hash_basic": sample_id_hash(["s1", "s2", "s3"]),
        "sample_id_hash_empty": sample_id_hash([]),
    }


@pytest.fixture(scope="module")
def pipeline_values(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    return _pipeline(tmp_path_factory.mktemp("golden"))


def test_raw_read_and_resample_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["raw_one_minute_sha256"] == GOLDEN["raw_one_minute_sha256"]
    assert pipeline_values["five_minute_sha256"] == GOLDEN["five_minute_sha256"]


def test_train_bars_loading_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["train_bars_sha256"] == GOLDEN["train_bars_sha256"]


def test_sample_event_loading_and_filtering_golden(
    pipeline_values: dict[str, object],
) -> None:
    assert (
        pipeline_values["sample_event_index_sha256"]
        == GOLDEN["sample_event_index_sha256"]
    )
    assert (
        pipeline_values["train_valid_events_sha256"]
        == GOLDEN["train_valid_events_sha256"]
    )


def test_train_inner_fold_manifest_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["fold_manifest_sha256"] == GOLDEN["fold_manifest_sha256"]


def test_feature_frame_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["feature_frame_sha256"] == GOLDEN["feature_frame_sha256"]
    assert (
        pipeline_values["feature_added_columns"] == GOLDEN["feature_added_columns"]
    )


def test_window_dataset_and_matrix_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["window_metadata_sha256"] == GOLDEN["window_metadata_sha256"]
    assert pipeline_values["window_matrix_sha256"] == GOLDEN["window_matrix_sha256"]
    assert pipeline_values["window_matrix_shape"] == GOLDEN["window_matrix_shape"]
    assert pipeline_values["window_matrix_dtype"] == GOLDEN["window_matrix_dtype"]


def test_fold_and_cap_indices_golden(pipeline_values: dict[str, object]) -> None:
    assert (
        pipeline_values["fold0_train_indices_sha256"]
        == GOLDEN["fold0_train_indices_sha256"]
    )
    assert pipeline_values["fold0_train_count"] == GOLDEN["fold0_train_count"]
    assert (
        pipeline_values["fold0_eval_indices_sha256"]
        == GOLDEN["fold0_eval_indices_sha256"]
    )
    assert pipeline_values["fold0_eval_count"] == GOLDEN["fold0_eval_count"]
    assert (
        pipeline_values["capped_fold0_train_indices"]
        == GOLDEN["capped_fold0_train_indices"]
    )


def test_sample_id_hash_golden(pipeline_values: dict[str, object]) -> None:
    assert pipeline_values["sample_id_hash_basic"] == GOLDEN["sample_id_hash_basic"]
    assert pipeline_values["sample_id_hash_empty"] == GOLDEN["sample_id_hash_empty"]
    assert sample_id_hash(["s2", "s1"]) != sample_id_hash(["s1", "s2"])


def test_require_feature_columns_exact_error() -> None:
    frame = pd.DataFrame({"log_return": [0.1], "time_of_day_sin": [0.0]})
    require_feature_columns(("log_return",), frame)
    with pytest.raises(ValueError) as excinfo:
        require_feature_columns(("log_return", "missing_a", "missing_b"), frame)
    assert "missing columns" in str(excinfo.value)
    assert "missing_a" in str(excinfo.value)
    assert "missing_b" in str(excinfo.value)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        print(json.dumps(_pipeline(Path(tmp)), indent=2))
