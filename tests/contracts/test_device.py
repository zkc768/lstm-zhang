from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import device  # noqa: E402


class _FakeCuda:
    def __init__(self, available: bool, name: str = "FakeGPU") -> None:
        self._available = available
        self._name = name

    def is_available(self) -> bool:
        return self._available

    def get_device_name(self, _device: object) -> str:
        return self._name


class _FakeDevice:
    def __init__(self, spec: str) -> None:
        self._spec = spec

    def __str__(self) -> str:
        return self._spec


class _FakeTorch:
    def __init__(self, cuda_available: bool) -> None:
        self.cuda = _FakeCuda(cuda_available)

    def device(self, spec: str) -> _FakeDevice:
        return _FakeDevice(spec)


def test_auto_falls_back_to_cpu_with_reason() -> None:
    resolved, reason = device.resolve_torch_device(_FakeTorch(False), "auto", require_gpu=False)
    assert str(resolved) == "cpu"
    assert reason == "cuda_unavailable"


def test_auto_prefers_cuda_when_available() -> None:
    resolved, reason = device.resolve_torch_device(_FakeTorch(True), "auto", require_gpu=False)
    assert str(resolved) == "cuda"
    assert reason is None


def test_require_gpu_without_cuda_fails_loudly() -> None:
    with pytest.raises(RuntimeError, match="GPU required"):
        device.resolve_torch_device(_FakeTorch(False), "auto", require_gpu=True)


def test_explicit_cuda_without_cuda_fails_loudly() -> None:
    with pytest.raises(RuntimeError, match="CUDA requested"):
        device.resolve_torch_device(_FakeTorch(False), "cuda", require_gpu=False)


def test_manifest_fields_record_full_provenance() -> None:
    fake = _FakeTorch(False)
    resolved, reason = device.resolve_torch_device(fake, "auto", require_gpu=False)
    fields = device.device_manifest_fields(fake, "auto", resolved, reason)
    assert fields == {
        "requested_device": "auto",
        "resolved_device": "cpu",
        "cuda_available": False,
        "gpu_name_or_null": None,
        "device_fallback_reason": "cuda_unavailable",
    }
