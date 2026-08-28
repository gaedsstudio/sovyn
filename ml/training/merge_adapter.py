from pathlib import Path
import shutil


def main() -> int:
    required_bytes = 20 * 1024 * 1024 * 1024
    available_bytes = shutil.disk_usage(Path.cwd()).free
    print("SOVYN Signal adapter merge")
    print(f"Estimated required: {required_bytes}")
    print(f"Available: {available_bytes}")
    if available_bytes < required_bytes:
        print("Not enough free disk space for merged model export")
        return 2
    print("Merge command is intentionally separate from training")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

