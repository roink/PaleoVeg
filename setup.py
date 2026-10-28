from setuptools import setup, find_packages

REPRODUCTION_REQUIREMENTS = [
    "pyarrow>=15",
    "rasterio>=1.3",
    "scipy>=1.11",
    "matplotlib>=3.8",
    "netCDF4>=1.6",
    "pyshp>=2.3",
]

# Read the contents of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="PaleoVeg",
    version="1.0.0",
    description="Predict paleovegetation from bioclimatic variables.",
    long_description=long_description,
    long_description_content_type="text/markdown",  # Specify Markdown format
    author="Philipp Schlüter",
    author_email="p.schlueter@uni-koeln.de",
    url="https://github.com/roink/PaleoVeg",
    packages=find_packages(),
    include_package_data=True,
    package_data={"paleoveg": ["model_metadata.json", "data/co2/*.csv", "data/co2/*.md"]},
    install_requires=[
        "scikit-learn==1.9.0",
        "numpy>=2.1.3",
        "pandas>=2.2.3",
        "requests",
    ],
    extras_require={
        # ``training`` remains as a compatibility alias for earlier instructions.
        "training": REPRODUCTION_REQUIREMENTS,
        "reproduction": REPRODUCTION_REQUIREMENTS,
        "test": ["pytest>=8"],
        "browser-test": ["pytest>=8", "selenium>=4"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
