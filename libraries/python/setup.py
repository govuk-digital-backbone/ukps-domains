import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ukpsdomains",
    version="0.0.1",
    author="OllieJC, GOV.UK Digital Backbone",
    author_email="digital-backbone+ukpsdomains@dsit.gov.uk",
    description="Utilities for checking emails and domains in the UKPS Domains data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/govuk-digital-backbone/ukps-domains",
    project_urls={
        "Bug Tracker": "https://github.com/govuk-digital-backbone/ukps-domains/issues",
        "UKPS Domains": "https://github.com/govuk-digital-backbone/ukps-domains",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Email",
        "Topic :: File Formats :: JSON",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords = [
        "domains",
        "ukps",
        "government",
        "public sector",
        "UK",
        "United Kingdom"
    ],
    package_dir={"ukpsdomains": "src"},
    packages=["ukpsdomains"],
    python_requires=">=3.6",
)
