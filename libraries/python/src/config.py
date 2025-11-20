from os.path import dirname
from pathlib import Path

DEFAULT_REMOTE_URL_PREFIX = "https://raw.githubusercontent.com/govuk-digital-backbone/ukps-domains/refs/heads/main/data/"
DEFAULT_REMOTE_TIMEOUT = 2  # seconds

DEFAULT_LOCAL_DIRECTORY = Path(dirname(__file__))

UKPSDOMAINS_FILES = ["user_domains.json", "govuk_organisations.json"]

METADATA_FILENAME = ".ukpsdomains_meta.json"
