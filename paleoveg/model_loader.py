"""Model acquisition and loading utilities.

The classifier is intentionally loaded lazily.  This keeps importing PaleoVeg
side-effect free and lets browser callers fetch the release asset themselves
before passing its bytes to :func:`load_model`.
"""

import bz2
import hashlib
import io
import os
import pickle
from pathlib import Path
from typing import BinaryIO, Optional, Union

from sklearn.ensemble import RandomForestClassifier


MODEL_FILENAME = "model.pkl.bz2"
MODEL_VERSION = "v0.1.2"
MODEL_SHA256 = "7ad80d07f91c2c0c51b1cad9f423056d24daf07ea70b7ab04ba4502d38d1fab6"
MODEL_URL = (
    "https://github.com/roink/PaleoVeg/releases/download/"
    f"{MODEL_VERSION}/{MODEL_FILENAME}"
)

ModelSource = Union[str, os.PathLike, bytes, bytearray, memoryview, BinaryIO]
_cached_model = None


def default_model_path() -> Path:
    """Return the package-local path used by native Python installations."""
    return Path(__file__).with_name(MODEL_FILENAME)


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


def _open_compressed_source(source: ModelSource):
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bz2.BZ2File(io.BytesIO(bytes(source)), "rb")
    if hasattr(source, "read"):
        return bz2.BZ2File(source, "rb")
    return bz2.BZ2File(Path(source), "rb")


def load_model(source: Optional[ModelSource] = None):
    """Load and validate the PaleoVeg classifier.

    Args:
        source: A path, compressed model bytes, or binary file object. When it
            is omitted, the released model is downloaded and cached locally.

    Models loaded from an explicit source are not placed in the module cache;
    this makes tests and browser sessions deterministic.
    """
    global _cached_model

    if source is None and _cached_model is not None:
        return _cached_model

    resolved_source = download_model() if source is None else source
    with _open_compressed_source(resolved_source) as compressed_file:
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
