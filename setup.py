from setuptools import setup, find_packages

setup(
    name="PaleoVeg",
    version="0.1.0",
    description="Predict paleovegetation from bioclimatic variables.",
    author="Your Name",
    author_email="your_email@example.com",
    url="https://github.com/roink/PaleoVeg",  # Replace with actual URL
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "scikit-learn>=1.0",
        "numpy>=1.21",
        pandas,
        joblib,
        matplotlib,
        cartopy,
        pickle,
        bz2
    ],
    package_data={
        "paleoveg": ["model.pkl.bz2"],  # Include the model file
    },
    python_requires=">=3.6",
)

