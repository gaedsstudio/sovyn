import argparse
import importlib.metadata
import importlib.util
import json
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HardwareReport:
    os: str
    python: str
    pytorch: str | None
    cuda_available: bool
    cuda_version: str | None
    gpu_model: str | None
    vram_total_gb: float | None
    bf16_supported: bool | None
    compute_capability: str | None
    transformers: str | None
    bitsandbytes_available: bool
    flash_attention_available: bool


def detect_hardware() -> HardwareReport:
    torch = _load_torch()
    cuda_available = bool(torch is not None and torch.cuda.is_available())
    gpu_model = None
    vram_total_gb = None
    bf16_supported = None
    compute_capability = None
    cuda_version = None
    pytorch = _package_version("torch")
    if torch is not None:
        cuda_version = torch.version.cuda
    if cuda_available and torch is not None:
        props = torch.cuda.get_device_properties(0)
        gpu_model = torch.cuda.get_device_name(0)
        vram_total_gb = round(props.total_memory / (1024**3), 2)
        bf16_supported = bool(torch.cuda.is_bf16_supported())
        major, minor = torch.cuda.get_device_capability(0)
        compute_capability = f"{major}.{minor}"
    return HardwareReport(
        os=platform.platform(),
        python=sys.version.split()[0],
        pytorch=pytorch,
        cuda_available=cuda_available,
        cuda_version=cuda_version,
        gpu_model=gpu_model,
        vram_total_gb=vram_total_gb,
        bf16_supported=bf16_supported,
        compute_capability=compute_capability,
        transformers=_package_version("transformers"),
        bitsandbytes_available=importlib.util.find_spec("bitsandbytes") is not None,
        flash_attention_available=importlib.util.find_spec("flash_attn") is not None,
    )


def render_report(report: HardwareReport) -> str:
    rows = (
        ("OS", report.os),
        ("Python", report.python),
        ("PyTorch", report.pytorch or "unavailable"),
        ("CUDA", report.cuda_version or "unavailable"),
        ("GPU", report.gpu_model or "unavailable"),
        ("VRAM", f"{report.vram_total_gb:.2f} GB" if report.vram_total_gb is not None else "unavailable"),
        ("BF16", _support(report.bf16_supported)),
        ("Compute capability", report.compute_capability or "unavailable"),
        ("transformers", report.transformers or "unavailable"),
        ("bitsandbytes", "available" if report.bitsandbytes_available else "unavailable"),
        ("flash attention", "available" if report.flash_attention_available else "unavailable"),
    )
    body = "\n".join(f"{name:<20}{value}" for name, value in rows)
    return f"SOVYN Hardware Report\n\n{body}"


def save_report(report: HardwareReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=Path("outputs/hardware_report.json"))
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = detect_hardware()
    print(render_report(report))
    if not args.no_save:
        save_report(report, args.json_output)
    return 0


def _package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def _load_torch():
    if importlib.util.find_spec("torch") is None:
        return None
    import torch

    return torch


def _support(value: bool | None) -> str:
    if value is None:
        return "unavailable"
    return "supported" if value else "unsupported"


if __name__ == "__main__":
    raise SystemExit(main())
