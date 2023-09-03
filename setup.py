
# Always prefer setuptools over distutils
from setuptools import setup

# To use a consistent encoding
from codecs import open
from os import path

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# This call to setup() does all the work
setup(
    name="bluecon",
    version="0.0.1a4",
    description="Library for connecting to Fermax Blue supported doorbells",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://bluecon.afonsogarcia.dev",
    author="Afonso Garcia",
    author_email="bluecon@afonsogarcia.dev",
    license="MIT",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries"
    ],
    packages=["bluecon"],
    include_package_data=True,
    install_requires=["aiohttp", "oscrypto", "protobuf", "http-ece"]
)