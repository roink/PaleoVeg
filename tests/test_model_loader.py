import bz2
import pickle

import pytest

from paleoveg.model_loader import load_model


def test_load_model_rejects_wrong_pickle_type():
    payload = bz2.compress(pickle.dumps({"not": "a classifier"}))
    with pytest.raises(ValueError, match="RandomForestClassifier"):
        load_model(payload)
