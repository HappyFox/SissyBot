"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name="sissybot",  # Required
    version="0.0.0",  # Required
    description="SissyBot control program.",  # Optional
    author="Keith Baston",
    author_email="keith.baston@gmail.com",
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[  # Optional
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: robot control",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["sissyBot"],
    python_requires=">=3.7",
    install_requires=["kivy"],
    entry_points="""
        [console_scripts]
        sb=sissyBot.cli:cli
    """,
    project_urls={"Source": "https://github.com/HappyFox/SissyBot"},  # Optional
)
