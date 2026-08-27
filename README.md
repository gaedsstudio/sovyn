# SOVYN

The intelligence layer for the global economy.

This repository currently includes the SOVYN model fine-tuning subsystem under
`training/`. It is designed for storage-constrained development: 4-bit QLoRA by
default, shared Hugging Face cache reuse, streaming datasets, adapter-only
outputs, bounded checkpoints, and dry-run validation before training.

## Training Quick Start

```bash
cd training
uv run sovyn-train train --dry-run
uv run sovyn-train storage
uv run pytest
```

Heavy model training dependencies are optional. The default test and dry-run
paths do not download model weights or datasets.

