from pathlib import Path


class SovynTrainingError(Exception):
    pass


class ConfigFileError(SovynTrainingError):
    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.path = path

    def __str__(self) -> str:
        return f"training config file does not exist: {self.path}"


class DiskSpaceError(SovynTrainingError):
    __slots__ = ("available_bytes", "required_bytes")

    def __init__(self, available_bytes: int, required_bytes: int) -> None:
        super().__init__(available_bytes, required_bytes)
        self.available_bytes = available_bytes
        self.required_bytes = required_bytes

    def __str__(self) -> str:
        return (
            "insufficient disk space: "
            f"available={self.available_bytes}, required={self.required_bytes}"
        )


class DatasetFormatError(SovynTrainingError):
    __slots__ = ("line_number", "path")

    def __init__(self, path: Path, line_number: int) -> None:
        super().__init__(path, line_number)
        self.path = path
        self.line_number = line_number

    def __str__(self) -> str:
        return f"invalid JSONL sample at {self.path}:{self.line_number}"


class ZstdDependencyError(SovynTrainingError):
    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.path = path

    def __str__(self) -> str:
        return f"zstandard is required to stream compressed dataset: {self.path}"


class MergeExportError(SovynTrainingError):
    __slots__ = ("available_bytes", "required_bytes")

    def __init__(self, required_bytes: int, available_bytes: int) -> None:
        super().__init__(required_bytes, available_bytes)
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes

    def __str__(self) -> str:
        return (
            "merged model export requires explicit disk capacity: "
            f"required={self.required_bytes}, available={self.available_bytes}"
        )
