from __future__ import annotations

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
