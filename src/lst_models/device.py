from __future__ import annotations

import importlib
from typing import Any


def resolve_torch_device(
    torch_module: Any, requested_device: str = "auto", require_gpu: bool = False
) -> tuple[Any, str | None]:
    """Resolve a torch device with CUDA preference.

    Returns the device and a fallback reason (``None`` when no fallback was
    needed). Fails loudly when GPU is required but unavailable, or when an
    explicit CUDA device is requested but unavailable.
    """
    cuda_available = bool(torch_module.cuda.is_available())
    if requested_device == "auto":
        if cuda_available:
            return torch_module.device("cuda"), None
        if require_gpu:
            raise RuntimeError("GPU required, but torch.cuda.is_available() is False")
        return torch_module.device("cpu"), "cuda_unavailable"
    if str(requested_device).startswith("cuda") and not cuda_available:
        raise RuntimeError("CUDA requested, but torch.cuda.is_available() is False")
    return torch_module.device(requested_device), None


def device_manifest_fields(
    torch_module: Any,
    requested_device: str,
    resolved_device: Any,
    fallback_reason: str | None,
) -> dict[str, Any]:
    """Build the AGENTS.md GPU/CUDA manifest fields for a training run."""
    cuda_available = bool(torch_module.cuda.is_available())
    resolved = str(resolved_device)
    gpu_name: str | None = None
    if cuda_available and resolved.startswith("cuda"):
        gpu_name = str(torch_module.cuda.get_device_name(resolved_device))
    return {
        "requested_device": str(requested_device),
        "resolved_device": resolved,
        "cuda_available": cuda_available,
        "gpu_name_or_null": gpu_name,
        "device_fallback_reason": fallback_reason,
    }


def torch_gpu_name_or_null(torch_module: Any) -> str | None:
    if not bool(torch_module.cuda.is_available()):
        return None
    try:
        return str(torch_module.cuda.get_device_name(0))
    except Exception:
        return None


def non_gpu_device_info() -> dict[str, str]:
    return {
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_probe",
    }


def detect_torch_runtime(forced_import_error: str | None = None) -> tuple[bool, str | None, str]:
    """Probe the torch runtime without requiring torch to be installed.

    ``forced_import_error`` lets a stage report a previously captured torch
    import failure (or a test-injected one) instead of importing torch again.
    """
    if forced_import_error:
        return False, None, forced_import_error
    try:
        import torch
    except ModuleNotFoundError as exc:
        return False, None, f"torch import failed: {exc}"
    cuda_available = bool(torch.cuda.is_available())
    return cuda_available, torch_gpu_name_or_null(torch), "" if cuda_available else "cuda_unavailable"


def torch_runtime_device_fields() -> dict[str, Any]:
    try:
        torch_module = importlib.import_module("torch")
    except (ImportError, ModuleNotFoundError, OSError):
        return {"cuda_available": False, "gpu_name_or_null": None}

    cuda_available = bool(torch_module.cuda.is_available())
    gpu_name: str | None = None
    if cuda_available:
        try:
            gpu_name = str(torch_module.cuda.get_device_name(0))
        except (AttributeError, RuntimeError, ValueError):
            gpu_name = None
    return {"cuda_available": cuda_available, "gpu_name_or_null": gpu_name}
