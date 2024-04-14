from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as f:
    long_descrition=f.read()

setup(
    name="fast_gmail",
    version="1.0.0",
    description="GmailApi wrapper",
    long_description=long_descrition,  # Load description from README
    long_description_content_type='text/markdown',
    author="Aleti",
    author_email="aleti.open.source@gmail.com",
    url="https://github.com/aleti1/fast_gmail",
    license="MIT",
    requires=[],
    package_dir={"":"fast_gmail"},
    packages=find_packages(where="fast_gmail"),
    python_requires=">=3.10",
    install_requires=[
        "cachetools==5.3.3",
        "certifi==2024.2.2",
        "charset-normalizer==3.3.2",
        "google-api-core==2.18.0",
        "google-api-python-client==2.125.0",
        "google-auth==2.29.0",
        "google-auth-httplib2==0.2.0",
        "google-auth-oauthlib==1.2.0",
        "googleapis-common-protos==1.63.0",
        "httplib2==0.22.0",
        "idna==3.7",
        "oauthlib==3.2.2",
        "proto-plus==1.23.0",
        "protobuf==4.25.3",
        "pyasn1==0.6.0",
        "pyasn1_modules==0.4.0",
        "pyparsing==3.1.2",
        "requests==2.31.0",
        "requests-oauthlib==2.0.0",
        "rsa==4.9",
        "typing_extensions==4.11.0",
        "uritemplate==4.1.1",
        "urllib3==2.2.1",
    ],
)
