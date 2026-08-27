.PHONY: train-storage train-dry-run train-test

train-storage:
	cd training && uv run sovyn-train storage

train-dry-run:
	cd training && uv run sovyn-train train --dry-run

train-test:
	cd training && uv run pytest

