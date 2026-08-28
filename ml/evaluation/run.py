from pathlib import Path

from ml.evaluation.benchmark import run_benchmark


def main() -> int:
    report = run_benchmark("mock", Path("ml/datasets/sovyn-v1/test.jsonl"))
    print("SOVYN Signal evaluation")
    for metric, value in report["metrics"].items():
        print(f"{metric}: {value:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
