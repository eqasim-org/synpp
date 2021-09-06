from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding = "utf-8") as f:
    long_description = f.read()

setup(
    name = "synpp",
    version = "1.5.0",
    description = "Synthetic population pipeline package for eqasim",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/eqasim-org/synpp",
    author = "Sebastian Hörl",
    author_email = "hoerl.sebastian@gmail.com",
    keywords = "pipeline automation synthetic population dependency management transport",
    package_dir = { "": "src" },
    packages = find_packages(where = "src"),
    python_requires='>=3.0',
    install_requires = ["networkx>=2.4", "PyYAML>=5.1.2", "pyzmq>=18.1.0"],
    extras_require = {
        "test": ["pytest>=5.3.1"], "example": ["pandas>=0.25.3"]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering",
    ],
)
