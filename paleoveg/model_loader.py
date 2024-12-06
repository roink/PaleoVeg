import os
import requests
import bz2
import pickle
from sklearn.ensemble import RandomForestClassifier

def download_model():
    """Download the model file from GitHub Releases if it does not exist locally."""
    model_path = os.path.join(os.path.dirname(__file__), "model.pkl.bz2")
    if not os.path.exists(model_path):
        url = "https://github.com/roink/PaleoVeg/releases/download/v1.0.0/model.pkl.bz2"
        print(f"Downloading model from {url}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(model_path, "wb") as f:
                f.write(response.content)
            print("Download complete.")
        else:
            raise Exception(f"Failed to download model. HTTP Status: {response.status_code}")
    return model_path

def load_model():
    """
    Load the compressed model and validate its type.

    Returns:
        model: The loaded Random Forest Classifier.

    Raises:
        ValueError: If the loaded model is not a RandomForestClassifier.
    """
    model_path = download_model()  # Ensure the model is downloaded

    # Load the model
    with bz2.BZ2File(model_path, "rb") as f:
        model = pickle.load(f)

    # Validate the loaded model
    if not isinstance(model, RandomForestClassifier):
        raise ValueError(f"The loaded model is not a RandomForestClassifier. Loaded type: {type(model)}")

    return model


