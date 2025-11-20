import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

try:
    import requests
    USE_REQUESTS = True
except ImportError:
    requests = None
    USE_REQUESTS = False

from .config import (
    DEFAULT_REMOTE_URL_PREFIX,
    DEFAULT_REMOTE_TIMEOUT,
    DEFAULT_LOCAL_DIRECTORY,
    UKPSDOMAINS_FILES,
    METADATA_FILENAME
)

MetadataType = Dict[str, Dict[str, Any]]

class UKPSDomains:
    def __init__(
        self,
        remote_url_prefix: str = DEFAULT_REMOTE_URL_PREFIX,
        local_directory: Union[str, Path] = DEFAULT_LOCAL_DIRECTORY,
        files: List[str] = UKPSDOMAINS_FILES,
        remote_timeout: int = DEFAULT_REMOTE_TIMEOUT,
        allow_remote: bool = True
    ) -> None:
        self.remote_url_prefix = remote_url_prefix.strip().rstrip("/")
        self.remote_timeout = remote_timeout
        self.allow_remote = allow_remote

        self.local_directory = Path(local_directory)
        self.files = files

        self.data_source = None
        self._data = {}

        self.refresh()
    

    def refresh(self, allow_remote: Optional[bool] = None) -> bool:
        fetch_success = False

        if allow_remote is not None:
            self.allow_remote = allow_remote

        fetch_success = self._fetch_remote()
        if fetch_success:
            self.data_source = "remote"

        if not fetch_success:
            fetch_success = self._load_local()
            if fetch_success:
                self.data_source = "local"

        if not fetch_success:
            raise RuntimeError("Failed to load UKPS Domains data from both remote and local sources.")


    def _fetch_remote(self) -> bool:
        if not USE_REQUESTS:
            return False

        if not self.allow_remote:
            return False
        
        res = False

        for file in self.files:
            url = f"{self.remote_url_prefix}/{file}"
            try:
                response = requests.get(url, timeout=self.remote_timeout)
                response.raise_for_status()
                self._data[file] = response.json()
                res = True
            except Exception as e:
                print(f"An error occurred: {e}")
                res = False
                break

        return res

    def _load_local(self) -> bool:
        res = False

        for file in self.files:
            path = self.local_directory / file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data[file] = json.load(f)
                    res = True
            except Exception as e:
                print(f"An error occurred: {e}")
                res = False
                break

        return res

    def _normalise_domain(self, domain: str = None) -> str:
        res_domain = None
        if domain is not None:
            res_domain = domain.strip().lower().rstrip(".")
        if res_domain is None or "." not in res_domain:
            raise ValueError("Domain invalid")
        return res_domain

    def is_ukps_domain(self, domain: str) -> bool:
        ctx = self.organisational_context_for_domain(domain, with_govuk_data=False)
        is_valid = ctx is not None and ctx.get("domain_pattern", None) is not None
        return is_valid

    def _extract_domain_from_email(self, email: str = None) -> str:
        if not email or "@" not in email:
            return None
        return email.rsplit("@", 1)[1]

    def is_ukps_email(self, email: str) -> bool:
        ctx = self.organisational_context_for_email(email, with_govuk_data=False)
        is_valid = ctx is not None and ctx.get("domain_pattern", None) is not None
        return is_valid

    def organisational_context_for_domain(self, domain: str = None, with_govuk_data: bool = True) -> dict:
        if not self.data_source:
            raise RuntimeError("Data not loaded. Call refresh() first.")

        domain = self._normalise_domain(domain)

        res = None
        maybe_res = None

        for entry in self._data.get("user_domains.json", []):
            pattern = entry.get("domain_pattern", "")
            if pattern:
                if domain == pattern:
                    res = entry
                    break
                if pattern.startswith("*."):
                    suffix = pattern[1:]
                    if domain.endswith(suffix):
                        maybe_res = entry

        if not res and maybe_res:
            res = maybe_res

        if res and res.get("organisation_id") and with_govuk_data:
            govuk_data = self._data.get("govuk_organisations.json", {}).get(res["organisation_id"], {})
            if govuk_data:
                res["govuk_data"] = govuk_data

        return res

    def organisational_context_for_email(self, email: str = None, with_govuk_data: bool = True) -> dict:
        domain = self._extract_domain_from_email(email)
        return self.organisational_context_for_domain(domain, with_govuk_data=with_govuk_data)

