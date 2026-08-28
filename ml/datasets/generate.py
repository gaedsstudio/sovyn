from pathlib import Path

from ml.datasets.generate_v1 import build_dataset as build_v1_dataset


def build_dataset(root: Path = Path("ml/datasets")) -> None:
    build_v1_dataset(root=root / "sovyn-v1", examples=64, seed=42)


if __name__ == "__main__":
    build_dataset()
