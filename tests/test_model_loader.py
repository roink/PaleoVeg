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
