import bz2
import pickle

import pytest

from paleoveg.model_loader import load_model


def test_load_model_rejects_wrong_pickle_type():
    payload = bz2.compress(pickle.dumps({"not": "a classifier"}))
    with pytest.raises(ValueError, match="RandomForestClassifier"):
        load_model(payload)


def test_load_model_reports_compressed_file_progress(tmp_path):
    model_path = tmp_path / "model.pkl.bz2"
    model_path.write_bytes(bz2.compress(pickle.dumps({"not": "a classifier"})))
    progress = []

    with pytest.raises(ValueError, match="RandomForestClassifier"):
        load_model(model_path, progress_callback=progress.append)

    assert progress[-1] == 1.0
    assert progress == sorted(progress)


def test_download_keeps_old_classifier_separate(monkeypatch, tmp_path):
    import hashlib
    import requests
    from paleoveg import model_loader

    legacy = tmp_path / "model.pkl.bz2"
    legacy.write_bytes(b"previous release")
    payload = b"new release classifier"
    monkeypatch.setattr(model_loader, "__file__", str(tmp_path / "model_loader.py"))
    monkeypatch.setattr(model_loader, "MODEL_SHA256", hashlib.sha256(payload).hexdigest())

    class Response:
        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield payload

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response())
    downloaded = model_loader.download_model()
    assert downloaded != legacy
    assert downloaded.read_bytes() == payload
    assert legacy.read_bytes() == b"previous release"
