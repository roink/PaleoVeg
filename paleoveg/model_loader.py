"""Model acquisition and loading utilities.

The classifier is intentionally loaded lazily.  This keeps importing PaleoVeg
side-effect free and lets browser callers fetch the release asset themselves
before passing its bytes to :func:`load_model`.
"""

import bz2
import hashlib
import io
import json
import os
import pickle
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Callable, Iterator, Optional, Union

from sklearn.ensemble import RandomForestClassifier


_metadata = json.loads(Path(__file__).with_name("model_metadata.json").read_text())
MODEL_FILENAME = _metadata["filename"]
MODEL_VERSION = _metadata["version"]
MODEL_SHA256 = _metadata["sha256"]
MODEL_URL = (
    "https://github.com/roink/PaleoVeg/releases/download/"
    f"{MODEL_VERSION}/{MODEL_FILENAME}"
)

ModelSource = Union[str, os.PathLike, bytes, bytearray, memoryview, BinaryIO]
ProgressCallback = Callable[[float], None]
_cached_model = None


def default_model_path() -> Path:
    """Keep each released classifier in its own package-local cache file."""
    return Path(__file__).with_name(f"model-{MODEL_VERSION}.pkl.bz2")


def download_model(model_path: Optional[Union[str, os.PathLike]] = None) -> Path:
    """Download the released classifier if it is not already available.

    ``requests`` is imported only here so browser users that supply model bytes
    do not need Python networking at all.
    """
    path = Path(model_path) if model_path is not None else default_model_path()
    if path.exists() and _file_sha256(path) == MODEL_SHA256:
        return path
    if path.exists():
        raise ValueError(f"Existing model file failed its SHA-256 check: {path}")

    import requests

    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(MODEL_URL, timeout=120, stream=True)
    response.raise_for_status()
    temporary_path = path.with_suffix(path.suffix + ".part")
    digest = hashlib.sha256()
    with temporary_path.open("wb") as model_file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                digest.update(chunk)
                model_file.write(chunk)
    if digest.hexdigest() != MODEL_SHA256:
        temporary_path.unlink(missing_ok=True)
        raise ValueError("Downloaded model failed its SHA-256 integrity check.")
    temporary_path.replace(path)
    return path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _ProgressReader:
    """Report compressed-source progress while ``BZ2File`` consumes it."""

    def __init__(self, raw: BinaryIO, total_bytes: int, callback: ProgressCallback):
        self._raw = raw
        self._total_bytes = total_bytes
        self._callback = callback
        self._last_reported = -1.0

    def _report_progress(self) -> None:
        fraction = min(self._raw.tell() / self._total_bytes, 1.0) if self._total_bytes else 1.0
        if fraction < 1.0 and fraction - self._last_reported < 0.02:
            return
        self._last_reported = fraction
        try:
            self._callback(fraction)
        except Exception:
            # Progress reporting must never make model loading fail.
            pass

    def read(self, size: int = -1) -> bytes:
        data = self._raw.read(size)
        self._report_progress()
        return data

    def readinto(self, buffer) -> int:
        count = self._raw.readinto(buffer)
        self._report_progress()
        return count

    def __getattr__(self, name):
        return getattr(self._raw, name)


@contextmanager
def _open_compressed_source(
    source: ModelSource, progress_callback: Optional[ProgressCallback] = None
) -> Iterator[bz2.BZ2File]:
    if isinstance(source, (bytes, bytearray, memoryview)):
        with bz2.BZ2File(io.BytesIO(bytes(source)), "rb") as compressed:
            yield compressed
        return
    if hasattr(source, "read"):
        with bz2.BZ2File(source, "rb") as compressed:
            yield compressed
        return
    path = Path(source)
    with path.open("rb") as raw:
        wrapped = (
            _ProgressReader(raw, path.stat().st_size, progress_callback)
            if progress_callback is not None
            else raw
        )
        with bz2.BZ2File(wrapped, "rb") as compressed:
            yield compressed


def load_model(
    source: Optional[ModelSource] = None,
    progress_callback: Optional[ProgressCallback] = None,
):
    """Load and validate the PaleoVeg classifier.

    Args:
        source: A path, compressed model bytes, or binary file object. When it
            is omitted, the released model is downloaded and cached locally.
        progress_callback: Receives the fraction of compressed model bytes read
            when loading from a path. It is intended for browser progress UI.

    Models loaded from an explicit source are not placed in the module cache;
    this makes tests and browser sessions deterministic.
    """
    global _cached_model

    if source is None and _cached_model is not None:
        return _cached_model

    resolved_source = download_model() if source is None else source
    with _open_compressed_source(resolved_source, progress_callback) as compressed_file:
        model = pickle.load(compressed_file)

    if not isinstance(model, RandomForestClassifier):
        raise ValueError(
            "The loaded model is not a RandomForestClassifier. "
            f"Loaded type: {type(model)}"
        )

    if source is None:
        _cached_model = model
    return model


def clear_model_cache():
    """Clear the in-process model cache (primarily useful for tests)."""
    global _cached_model
    _cached_model = None
