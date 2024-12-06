from setuptools import setup, find_packages

setup(
    name="PaleoVeg",
    version="0.1.0",
    description="Predict paleovegetation from bioclimatic variables.",
    author="Philipp Schlüter",
    author_email="p.schlueter@uni-koeln.de",
    url="https://github.com/roink/PaleoVeg",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "scikit-learn>=1.0",
        "numpy>=1.21",
        "pandas",
        "joblib",
        "matplotlib",
        "cartopy",
    ],
    package_data={
        "paleoveg": ["model.pkl.bz2"],  # Include the model file
    },
    python_requires=">=3.6",
)

