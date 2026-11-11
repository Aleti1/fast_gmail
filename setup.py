from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as f:
    long_descrition = f.read()

setup(
    name="fast_gmail",
    version="1.5.0",
    description="GmailApi wrapper",
    long_description=long_descrition,
    long_description_content_type="text/markdown",
    author="Aleti",
    author_email="aleti.open.source@gmail.com",
    url="https://github.com/aleti1/fast_gmail",
    license="MIT",
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        "google-api-python-client >= 2.202.0, < 3",
        "google-auth-httplib2 >= 0.4.4, < 1",
        "google-auth-oauthlib >= 1.5.0, < 2",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=("fast_gmail", "fast_gmail.*")),
)
