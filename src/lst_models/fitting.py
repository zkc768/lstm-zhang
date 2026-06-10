"""Shared probe/trial model-fit wrappers for stage screening and HPO.

Plain functions only: no trainer abstraction, no callback system, no plugin
registry (route guide, "What Not To Build"). Stages own their ledgers and
orchestration; this module owns the per-fold fit/predict mechanics shared by
Stage 01 probes and Stage 02 HPO trials.

``TORCH_IMPORT_ERROR`` caches a failed torch import (or a test-injected
disable) so repeated torch probes fail fast with the same recorded reason
instead of retrying the import per fold.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models.config import require_mapping
from lst_models.device import (
    device_manifest_fields,
    non_gpu_device_info,
    resolve_torch_device,
)
from lst_models.metrics import (
    block_delta_macro_f1,
    score_classifier,
    ticker_delta_macro_f1,
)
from lst_models.models.ms_dlinear_tcn import MSDLinearTCNTiny
from lst_models.models.standard_dlinear import StandardDLinearTiny
from lst_models.models.tcn import TCNTiny
from lst_models.windows import sample_id_hash


TORCH_IMPORT_ERROR: str | None = None


@dataclass(frozen=True)
class ProbeFitResult:
    predictions: np.ndarray
    scores: np.ndarray
    requested_device: str
    resolved_device: str
    cuda_available: bool | None
    gpu_name_or_null: str | None
    device_fallback_reason: str
    best_iteration: int | None = None
    early_stopping_source: str = "not_applicable"
    early_stopping_used: bool = False
    early_stopping_reason: str = "not_configured"
    early_stopping_train_sample_id_hash: str = ""
    early_stopping_eval_sample_id_hash: str = ""


def probe_defaults(config: Mapping[str, Any], probe_id: str) -> Mapping[str, Any]:
    probe_config = require_mapping(config["lightweight_probes"][probe_id], f"lightweight_probes.{probe_id}")
    return require_mapping(probe_config.get("fixed_defaults", {}), f"lightweight_probes.{probe_id}.fixed_defaults")


def fit_probe(
    probe_id: str,
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    eval_meta: pd.DataFrame,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
    baseline_predictions: np.ndarray,
) -> dict[str, Any]:
    y_train = train_meta["label"].to_numpy(dtype=int)
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    if len(np.unique(y_train)) < 2:
        return {
            "fit_status": "failed_single_class_train",
            "error_message": "train-inner fold train labels contain fewer than two classes",
        }
    try:
        if probe_id == "logreg_flat_control":
            predictions, prediction_scores = fit_logreg_probe(x_train, y_train, x_eval, config, seed)
            device_info = non_gpu_device_info()
        elif probe_id == "lightgbm_small":
            predictions, prediction_scores = fit_lightgbm_probe(x_train, y_train, x_eval, config, seed)
            device_info = non_gpu_device_info()
        elif probe_id in {"standard_dlinear_tiny", "tcn_tiny", "ms_dlinear_tcn_tiny"}:
            torch_result = fit_torch_sequence_probe(
                probe_id,
                x_train,
                y_train,
                x_eval,
                config,
                seed,
                window_size,
                n_features,
                train_meta=train_meta,
            )
            predictions = torch_result.predictions
            prediction_scores = torch_result.scores
            device_info = {
                "requested_device": torch_result.requested_device,
                "resolved_device": torch_result.resolved_device,
                "device_fallback_reason": torch_result.device_fallback_reason,
                "best_iteration": torch_result.best_iteration,
                "early_stopping_source": torch_result.early_stopping_source,
                "early_stopping_used": torch_result.early_stopping_used,
                "early_stopping_reason": torch_result.early_stopping_reason,
                "early_stopping_train_sample_id_hash": (
                    torch_result.early_stopping_train_sample_id_hash
                ),
                "early_stopping_eval_sample_id_hash": (
                    torch_result.early_stopping_eval_sample_id_hash
                ),
            }
        else:
            return {"fit_status": "skipped_unknown_probe", "error_message": f"{probe_id} not implemented"}
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        if "GPU required" in str(exc) or "CUDA requested" in str(exc):
            raise
        return {"fit_status": "failed_exception", "error_message": f"{type(exc).__name__}: {exc}"}

    scored = score_classifier(y_eval, predictions, y_score=prediction_scores)
    ticker_deltas, positive_ticker_count = ticker_delta_macro_f1(
        eval_meta, predictions, baseline_predictions
    )
    block_deltas = block_delta_macro_f1(eval_meta, predictions, baseline_predictions)
    return {
        "fit_status": "completed",
        "macro_f1": scored["macro_f1"],
        "balanced_accuracy": scored["balanced_accuracy"],
        "accuracy": scored["accuracy"],
        "roc_auc": scored["roc_auc"],
        "mcc": scored["mcc"],
        "error_message": "",
        "positive_ticker_count": int(positive_ticker_count),
        "ticker_delta_macro_f1_json": json.dumps(ticker_deltas, sort_keys=True),
        "block_delta_macro_f1_json": json.dumps(block_deltas, sort_keys=True),
        **device_info,
    }


def fit_logreg_probe(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    defaults = probe_defaults(config, "logreg_flat_control")
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(x_train)
    eval_scaled = scaler.transform(x_eval)
    model = LogisticRegression(
        solver=str(defaults.get("solver", "liblinear")),
        class_weight=defaults.get("class_weight", "balanced"),
        max_iter=int(defaults.get("max_iter", 2000)),
        random_state=seed,
    )
    model.fit(train_scaled, y_train)
    predictions = model.predict(eval_scaled).astype(int)
    scores = model.predict_proba(eval_scaled)[:, 1].astype(float)
    return predictions, scores


def fit_lightgbm_probe(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    from lightgbm import LGBMClassifier

    defaults = dict(probe_defaults(config, "lightgbm_small"))
    defaults.setdefault("n_estimators", 200)
    defaults.setdefault("learning_rate", 0.03)
    defaults.setdefault("max_depth", 6)
    defaults.setdefault("num_leaves", 31)
    defaults.setdefault("subsample", 0.9)
    defaults.setdefault("subsample_freq", 1)
    defaults.setdefault("colsample_bytree", 0.9)
    defaults.setdefault("class_weight", "balanced")
    model = LGBMClassifier(**defaults, random_state=seed, verbosity=-1)
    model.fit(x_train, y_train)
    predictions = model.predict(x_eval).astype(int)
    scores = model.predict_proba(x_eval)[:, 1].astype(float)
    return predictions, scores


def fit_torch_sequence_probe(
    probe_id: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
    *,
    train_meta: pd.DataFrame | None = None,
) -> ProbeFitResult:
    global TORCH_IMPORT_ERROR
    if TORCH_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(TORCH_IMPORT_ERROR)
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
    except (ImportError, OSError) as exc:
        TORCH_IMPORT_ERROR = f"torch import failed: {exc}"
        raise ModuleNotFoundError(TORCH_IMPORT_ERROR) from exc

    torch.manual_seed(seed)
    raw_train_3d = x_train.reshape(len(x_train), window_size, n_features).astype(np.float32)
    eval_3d = x_eval.reshape(len(x_eval), window_size, n_features).astype(np.float32)

    torch_defaults = require_mapping(
        require_mapping(config.get("probe_training_defaults", {}), "probe_training_defaults").get(
            "torch", {}
        ),
        "probe_training_defaults.torch",
    )
    fixed_defaults = probe_defaults(config, probe_id)
    requested_device = str(torch_defaults.get("device", "auto"))
    require_gpu = bool(torch_defaults.get("require_gpu", False))
    device, fallback_reason = resolve_torch_device(torch, requested_device, require_gpu)
    split = torch_inner_train_early_stopping_split(
        raw_train_3d, y_train, train_meta, torch_defaults
    )
    fit_3d = split["x_fit"]
    fit_y = split["y_fit"]
    mean = fit_3d.mean(axis=(0, 1), keepdims=True)
    std = fit_3d.std(axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    train_3d = (fit_3d - mean) / std
    eval_3d = (eval_3d - mean) / std
    stop_3d = split["x_stop"]
    if stop_3d is not None:
        stop_3d = (stop_3d - mean) / std

    if probe_id == "standard_dlinear_tiny":
        model = StandardDLinearTiny(window_size, n_features, fixed_defaults)
    elif probe_id == "tcn_tiny":
        model = TCNTiny(n_features, fixed_defaults)
    elif probe_id == "ms_dlinear_tcn_tiny":
        model = MSDLinearTCNTiny(window_size, n_features, fixed_defaults)
    else:
        raise ValueError(f"unsupported torch probe: {probe_id}")

    model.to(device)
    class_counts = np.array([(fit_y == 0).sum(), (fit_y == 1).sum()], dtype=np.float32)
    class_counts = np.where(class_counts == 0.0, 1.0, class_counts)
    class_weights = class_counts.sum() / (2.0 * class_counts)
    loss_fn = nn.CrossEntropyLoss(
        weight=torch.as_tensor(class_weights, dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(torch_defaults.get("learning_rate", 0.001)),
        weight_decay=float(torch_defaults.get("weight_decay", 0.0001)),
    )
    batch_size = int(torch_defaults.get("batch_size", 1024))
    epochs = int(torch_defaults.get("epochs", 8))
    patience = max(1, int(torch_defaults.get("early_stopping_patience", 8)))
    min_delta = float(torch_defaults.get("early_stopping_min_delta", 0.0))
    gradient_clip_norm = float(torch_defaults.get("gradient_clip_norm", 0.0) or 0.0)
    train_dataset = TensorDataset(
        torch.as_tensor(train_3d, dtype=torch.float32),
        torch.as_tensor(fit_y.astype(int), dtype=torch.long),
    )
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        train_dataset,
        batch_size=max(1, batch_size),
        shuffle=True,
        generator=generator,
    )
    stop_x_tensor = None
    stop_y_tensor = None
    if bool(split["early_stopping_used"]):
        stop_x_tensor = torch.as_tensor(stop_3d, dtype=torch.float32, device=device)
        stop_y_tensor = torch.as_tensor(split["y_stop"].astype(int), dtype=torch.long, device=device)
    best_loss = float("inf")
    best_epoch = 0
    best_state: dict[str, Any] | None = None
    no_improvement_epochs = 0
    epochs_completed = 0
    early_stopping_reason = str(split["early_stopping_reason"])
    for epoch in range(1, max(1, epochs) + 1):
        model.train()
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            if gradient_clip_norm > 0.0:
                nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
            optimizer.step()
        epochs_completed = epoch
        if stop_x_tensor is None or stop_y_tensor is None:
            continue
        model.eval()
        with torch.no_grad():
            stop_loss = float(loss_fn(model(stop_x_tensor), stop_y_tensor).detach().cpu().item())
        if stop_loss < best_loss - min_delta:
            best_loss = stop_loss
            best_epoch = epoch
            best_state = {
                name: value.detach().cpu().clone() for name, value in model.state_dict().items()
            }
            no_improvement_epochs = 0
            continue
        no_improvement_epochs += 1
        if no_improvement_epochs >= patience:
            early_stopping_reason = "patience_exhausted"
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    if bool(split["early_stopping_used"]) and early_stopping_reason == "configured_inner_train_subsplit":
        early_stopping_reason = "max_epochs_reached_after_inner_train_subsplit"
    best_iteration = best_epoch if best_epoch else epochs_completed

    model.eval()
    with torch.no_grad():
        logits = model(torch.as_tensor(eval_3d, dtype=torch.float32, device=device))
        probabilities = torch.softmax(logits, dim=1)[:, 1].cpu().numpy().astype(float)
        predictions = logits.argmax(dim=1).cpu().numpy().astype(int)
    device_fields = device_manifest_fields(torch, requested_device, device, fallback_reason)
    return ProbeFitResult(
        predictions=predictions,
        scores=probabilities,
        requested_device=str(device_fields["requested_device"]),
        resolved_device=str(device_fields["resolved_device"]),
        cuda_available=bool(device_fields["cuda_available"]),
        gpu_name_or_null=device_fields["gpu_name_or_null"],
        device_fallback_reason=str(device_fields["device_fallback_reason"] or ""),
        best_iteration=int(best_iteration) if best_iteration else None,
        early_stopping_source=str(split["early_stopping_source"]),
        early_stopping_used=bool(split["early_stopping_used"]),
        early_stopping_reason=early_stopping_reason,
        early_stopping_train_sample_id_hash=str(split["early_stopping_train_sample_id_hash"]),
        early_stopping_eval_sample_id_hash=str(split["early_stopping_eval_sample_id_hash"]),
    )


def torch_inner_train_early_stopping_split(
    train_3d: np.ndarray,
    y_train: np.ndarray,
    train_meta: pd.DataFrame | None,
    torch_defaults: Mapping[str, Any],
) -> dict[str, Any]:
    full_hash = ""
    if train_meta is not None and "sample_id" in train_meta.columns:
        full_hash = sample_id_hash(train_meta["sample_id"].astype(str).tolist())

    def full_train(reason: str, source: str = "disabled") -> dict[str, Any]:
        return {
            "x_fit": train_3d,
            "y_fit": y_train,
            "x_stop": None,
            "y_stop": None,
            "early_stopping_source": source,
            "early_stopping_used": False,
            "early_stopping_reason": reason,
            "early_stopping_train_sample_id_hash": full_hash,
            "early_stopping_eval_sample_id_hash": "",
        }

    mode = str(torch_defaults.get("early_stopping", "none"))
    if mode in {"none", "disabled", "false", ""}:
        return full_train("early_stopping_disabled")
    if mode != "inner_train_chronological_tail":
        raise ValueError(
            "Torch early_stopping must be none or inner_train_chronological_tail"
        )
    if train_meta is None or len(train_meta) != len(y_train):
        return full_train(
            "missing_or_misaligned_train_meta_for_early_stopping_subsplit",
            source="inner_train_chronological_tail",
        )
    if "sample_id" not in train_meta.columns:
        return full_train(
            "missing_sample_id_for_early_stopping_subsplit",
            source="inner_train_chronological_tail",
        )

    validation_fraction = float(torch_defaults.get("early_stopping_validation_fraction", 0.2))
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("torch early_stopping_validation_fraction must be between 0 and 1")
    minimum_eval = max(
        1, int(torch_defaults.get("minimum_early_stopping_validation_samples", 128))
    )
    minimum_train = max(1, int(torch_defaults.get("minimum_early_stopping_train_samples", 128)))
    n_samples = len(y_train)
    n_eval = max(minimum_eval, int(np.ceil(n_samples * validation_fraction)))
    if n_eval >= n_samples or n_samples - n_eval < minimum_train:
        return full_train(
            "insufficient_inner_train_rows_for_minimum_validation_subsplit",
            source="inner_train_chronological_tail",
        )

    meta = train_meta.reset_index(drop=True).copy()
    sort_columns = [
        column
        for column in ("target_timestamp", "trading_day", "ticker", "sample_id")
        if column in meta.columns
    ]
    if not sort_columns:
        return full_train(
            "missing_chronology_columns_for_early_stopping_subsplit",
            source="inner_train_chronological_tail",
        )
    ordered_index = meta.sort_values(sort_columns, kind="stable").index.to_numpy()
    fit_index = ordered_index[:-n_eval]
    stop_index = ordered_index[-n_eval:]
    if len(fit_index) < minimum_train or len(stop_index) < minimum_eval:
        return full_train(
            "insufficient_inner_train_rows_for_subsplit",
            source="inner_train_chronological_tail",
        )
    if len(np.unique(y_train[fit_index])) < 2 or len(np.unique(y_train[stop_index])) < 2:
        return full_train(
            "inner_train_early_stopping_subsplit_single_class",
            source="inner_train_chronological_tail",
        )
    return {
        "x_fit": train_3d[fit_index],
        "y_fit": y_train[fit_index],
        "x_stop": train_3d[stop_index],
        "y_stop": y_train[stop_index],
        "early_stopping_source": "inner_train_chronological_tail",
        "early_stopping_used": True,
        "early_stopping_reason": "configured_inner_train_subsplit",
        "early_stopping_train_sample_id_hash": sample_id_hash(
            meta.iloc[fit_index]["sample_id"].astype(str).tolist()
        ),
        "early_stopping_eval_sample_id_hash": sample_id_hash(
            meta.iloc[stop_index]["sample_id"].astype(str).tolist()
        ),
    }
