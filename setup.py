from setuptools import setup
from setuptools import find_packages

with open("fast_gmail/README.md", "r") as f:
    long_descrition=f.read()

setup(
    name="fast-gmail",
    version="1.0.0",
    description="GmailApi wrapper",
    long_description=long_descrition,  # Load description from README
    long_description_content_type='text/markdown',
    author="Aleti",
    author_email="aleti.open.source@gmail.com",
    url="https://github.com/aleti1/fast-gmail",
    license="MIT",
    requires=[],
    package_dir={"":"fast_gmail"},
    packages=find_packages(where="fast_gmail"),
    python_requires=">=3.10"
)
