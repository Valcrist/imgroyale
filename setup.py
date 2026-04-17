from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="imgroyale",
    version="0.1.1",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "numpy",
        "pillow",
        "imagehash",
        "scikit-image",
        "toolbox @ git+https://github.com/Valcrist/toolbox.git",
    ],
    url="https://github.com/Valcrist/imgroyale",
    author="Valcrist",
    author_email="github@valcrist.com",
    description="ImgRoyale deduplication tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
