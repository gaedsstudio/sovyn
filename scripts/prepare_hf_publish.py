import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=Path("outputs/experiments/exp001-qwen3-4b"))
    parser.add_argument("--repo-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("Prepared publish plan only. No files were uploaded.")
    print(f"Repository: {args.repo_id}")
    print(f"Adapter: {args.experiment / 'adapter'}")
    print(f"Model card: {args.experiment / 'MODEL_CARD.md'}")
    print(f"Report: {args.experiment / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
