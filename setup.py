from setuptools import setup, find_packages

# Read the contents of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="PaleoVeg",
    version="0.1.2",
    description="Predict paleovegetation from bioclimatic variables.",
    long_description=long_description,
    long_description_content_type="text/markdown",  # Specify Markdown format
    author="Philipp Schlüter",
    author_email="p.schlueter@uni-koeln.de",
    url="https://github.com/roink/PaleoVeg",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "scikit-learn>=1.5.2",
        "numpy>=2.1.3",
        "pandas>=2.2.3",
        "joblib",
        "matplotlib",
        "cartopy",
	"requests"
    ],
    package_data={
        "paleoveg": ["model.pkl.bz2"],  # Include the model file
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)

