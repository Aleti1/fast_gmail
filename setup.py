from setuptools import setup
from setuptools import find_packages

setup(
    name="fast-gmail",
    version="1.0.0",
    description="Complete gmail api wrapper",
    author="Aleti",
    author_email="aleti.open.source@gmail.com",
    url="https://github.com/aleti1/fast-gmail",
    license="MIT",
    requires=[],
    packages=find_packages(
        exclude=("tests*", "testing*")
    )
)
