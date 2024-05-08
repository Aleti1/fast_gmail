from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as f:
    long_descrition=f.read()

setup(
    name="fast_gmail",
    version="1.0.9",
    description="GmailApi wrapper",
    long_description=long_descrition,
    long_description_content_type='text/markdown',
    author="Aleti",
    author_email="aleti.open.source@gmail.com",
    url="https://github.com/aleti1/fast_gmail",
    license="MIT",
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "google-api-python-client == 2.125.0",
        "google-auth-httplib2 == 0.2.0",
        "google-auth-oauthlib == 1.2.0",
        "typing-extensions == 4.11.0"
    ],    
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=("examples",))
)
