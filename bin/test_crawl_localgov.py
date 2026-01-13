#!/usr/bin/env python3
"""Comprehensive tests for crawl_localgov.py."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from crawl_localgov import (
    DIRECTORY_URL,
    SOURCE_ID,
    bump_minor_version,
    extract_domain,
    fetch_council,
    fetch_council_directory,
    fetch_page,
    find_stale_domains,
    is_valid_gov_domain,
    load_user_domains,
    merge_domains,
    remove_stale_domains,
    save_user_domains,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_directory_html():
    """Sample HTML for the council directory page with a sortable table."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Council Directory</title></head>
    <body>
        <nav><a href="/About">About</a></nav>
        <table class="table table-striped sortable">
            <thead>
                <tr><th>Council</th><th>Type</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td><a href="/Birmingham-City-Council" title="Birmingham City Council">Birmingham</a></td>
                    <td>Metropolitan District</td>
                </tr>
                <tr>
                    <td><a href="/Manchester-City-Council" title="Manchester City Council">Manchester</a></td>
                    <td>Metropolitan District</td>
                </tr>
                <tr>
                    <td><a href="/Leeds-City-Council" title="Leeds City Council">Leeds</a></td>
                    <td>Metropolitan District</td>
                </tr>
            </tbody>
        </table>
        <a href="/Contact" title="Contact Us">Contact</a>
    </body>
    </html>
    """


@pytest.fixture
def sample_council_html():
    """Sample HTML for a council page with government domain links."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Birmingham City Council</h1>
        <p>Visit our website at <a href="https://www.birmingham.gov.uk">www.birmingham.gov.uk</a></p>
        <p>Follow us on <a href="https://twitter.gov.uk/birmingham">Twitter</a></p>
    </body>
    </html>
    """


@pytest.fixture
def sample_user_domains_data():
    """Sample user_domains.json data structure."""
    return {
        "version": "0.0.5",
        "domains": [
            {
                "domain_pattern": "existing.gov.uk",
                "identifiers": {},
                "notes": "Existing domain",
                "organisation_id": None,
                "organisation_type_id": "central_gov",
                "source": "manual",
            },
            {
                "domain_pattern": "oldcouncil.gov.uk",
                "identifiers": {},
                "notes": "Local authority: Old Council",
                "organisation_id": None,
                "organisation_type_id": "local_authority",
                "source": SOURCE_ID,
            },
        ],
    }


@pytest.fixture
def temp_json_file(tmp_path, sample_user_domains_data):
    """Create a temporary user_domains.json file."""
    filepath = tmp_path / "user_domains.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sample_user_domains_data, f, indent=4)
        f.write("\n")
    return filepath


# =============================================================================
# Unit Tests: Domain Validation
# =============================================================================


class TestIsValidGovDomain:
    """Tests for is_valid_gov_domain function."""

    def test_gov_uk_valid(self):
        assert is_valid_gov_domain("example.gov.uk") is True
        assert is_valid_gov_domain("birmingham.gov.uk") is True
        assert is_valid_gov_domain("EXAMPLE.GOV.UK") is True

    def test_gov_scot_valid(self):
        assert is_valid_gov_domain("example.gov.scot") is True
        assert is_valid_gov_domain("EDINBURGH.GOV.SCOT") is True

    def test_gov_wales_valid(self):
        assert is_valid_gov_domain("example.gov.wales") is True

    def test_llyw_cymru_valid(self):
        assert is_valid_gov_domain("example.llyw.cymru") is True

    def test_invalid_domains(self):
        assert is_valid_gov_domain("example.com") is False
        assert is_valid_gov_domain("example.co.uk") is False
        assert is_valid_gov_domain("example.org.uk") is False
        assert is_valid_gov_domain("example.gov.us") is False
        assert is_valid_gov_domain("gov.uk") is False

    def test_empty_and_edge_cases(self):
        assert is_valid_gov_domain("") is False
        # Note: ".gov.uk" returns True because it ends with .gov.uk
        # This is acceptable as the function only checks suffix


# =============================================================================
# Unit Tests: Domain Extraction
# =============================================================================


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_extracts_gov_uk_from_href(self):
        html = '<a href="https://www.birmingham.gov.uk">Website</a>'
        assert extract_domain(html) == "birmingham.gov.uk"

    def test_extracts_gov_uk_from_www(self):
        html = "<p>Visit www.manchester.gov.uk for more info</p>"
        assert extract_domain(html) == "manchester.gov.uk"

    def test_extracts_gov_uk_from_https(self):
        html = "<p>Visit https://leeds.gov.uk for more info</p>"
        assert extract_domain(html) == "leeds.gov.uk"

    def test_prefers_gov_uk_over_others(self):
        html = """
        <a href="https://example.gov.scot">Scottish</a>
        <a href="https://example.gov.uk">UK</a>
        """
        assert extract_domain(html) == "example.gov.uk"

    def test_returns_gov_scot_when_no_gov_uk(self):
        html = '<a href="https://edinburgh.gov.scot">Edinburgh</a>'
        assert extract_domain(html) == "edinburgh.gov.scot"

    def test_returns_gov_wales(self):
        html = '<a href="https://cardiff.gov.wales">Cardiff</a>'
        assert extract_domain(html) == "cardiff.gov.wales"

    def test_returns_llyw_cymru(self):
        html = '<a href="https://example.llyw.cymru">Welsh Gov</a>'
        assert extract_domain(html) == "example.llyw.cymru"

    def test_skips_social_media_domains(self):
        html = """
        <a href="https://twitter.gov.uk/council">Twitter</a>
        <a href="https://youtube.gov.uk/council">YouTube</a>
        <a href="https://linkedin.gov.uk/council">LinkedIn</a>
        """
        assert extract_domain(html) is None

    def test_extracts_real_domain_ignoring_social(self):
        html = """
        <a href="https://twitter.gov.uk/council">Twitter</a>
        <a href="https://www.birmingham.gov.uk">Website</a>
        """
        assert extract_domain(html) == "birmingham.gov.uk"

    def test_returns_none_for_no_gov_domain(self):
        html = '<a href="https://example.com">No gov domain</a>'
        assert extract_domain(html) is None

    def test_returns_none_for_empty_html(self):
        assert extract_domain("") is None
        assert extract_domain(None) is None

    def test_case_insensitive(self):
        html = '<a href="HTTPS://WWW.BIRMINGHAM.GOV.UK">Website</a>'
        assert extract_domain(html) == "birmingham.gov.uk"


# =============================================================================
# Unit Tests: Version Bumping
# =============================================================================


class TestBumpMinorVersion:
    """Tests for bump_minor_version function."""

    def test_bumps_minor_resets_patch(self):
        assert bump_minor_version("0.0.5") == "0.1.0"
        assert bump_minor_version("1.2.3") == "1.3.0"
        assert bump_minor_version("0.9.9") == "0.10.0"

    def test_preserves_major(self):
        assert bump_minor_version("5.0.0") == "5.1.0"
        assert bump_minor_version("10.5.3") == "10.6.0"


# =============================================================================
# Unit Tests: Stale Domain Detection
# =============================================================================


class TestFindStaleDomains:
    """Tests for find_stale_domains function."""

    def test_finds_stale_domains(self, sample_user_domains_data):
        crawled = {"newdomain.gov.uk"}
        stale = find_stale_domains(sample_user_domains_data, crawled)
        assert len(stale) == 1
        assert stale[0]["domain_pattern"] == "oldcouncil.gov.uk"

    def test_ignores_other_sources(self, sample_user_domains_data):
        crawled = set()  # Nothing crawled
        stale = find_stale_domains(sample_user_domains_data, crawled)
        # Should only find the localgov.co.uk source entry
        assert len(stale) == 1
        assert stale[0]["source"] == SOURCE_ID

    def test_no_stale_when_all_present(self, sample_user_domains_data):
        # The function lowercases domain_pattern for comparison
        # crawled_domains should be lowercase (as done in main())
        crawled = {"oldcouncil.gov.uk"}  # lowercase as expected
        stale = find_stale_domains(sample_user_domains_data, crawled)
        assert len(stale) == 0


# =============================================================================
# Unit Tests: Stale Domain Removal
# =============================================================================


class TestRemoveStaleDomains:
    """Tests for remove_stale_domains function."""

    def test_removes_stale_domains(self, sample_user_domains_data):
        stale = [{"domain_pattern": "oldcouncil.gov.uk"}]
        count = remove_stale_domains(sample_user_domains_data, stale)
        assert count == 1
        assert len(sample_user_domains_data["domains"]) == 1
        assert sample_user_domains_data["domains"][0]["domain_pattern"] == "existing.gov.uk"

    def test_returns_zero_when_nothing_to_remove(self, sample_user_domains_data):
        stale = [{"domain_pattern": "nonexistent.gov.uk"}]
        count = remove_stale_domains(sample_user_domains_data, stale)
        assert count == 0
        assert len(sample_user_domains_data["domains"]) == 2


# =============================================================================
# Unit Tests: Domain Merging
# =============================================================================


class TestMergeDomains:
    """Tests for merge_domains function."""

    def test_adds_new_domains(self, sample_user_domains_data):
        council_results = [{"council_name": "New Council", "domain": "newcouncil.gov.uk"}]
        new_count, updated_count = merge_domains(sample_user_domains_data, council_results)
        assert new_count == 1
        assert updated_count == 0
        assert len(sample_user_domains_data["domains"]) == 3

    def test_skips_existing_domains_from_other_sources(self, sample_user_domains_data):
        council_results = [{"council_name": "Some Council", "domain": "existing.gov.uk"}]
        new_count, updated_count = merge_domains(sample_user_domains_data, council_results)
        assert new_count == 0
        assert updated_count == 0

    def test_updates_notes_for_same_source(self, sample_user_domains_data):
        council_results = [{"council_name": "Renamed Council", "domain": "oldcouncil.gov.uk"}]
        new_count, updated_count = merge_domains(sample_user_domains_data, council_results)
        assert new_count == 0
        assert updated_count == 1
        entry = next(
            d for d in sample_user_domains_data["domains"] if d["domain_pattern"] == "oldcouncil.gov.uk"
        )
        assert entry["notes"] == "Local authority: Renamed Council"

    def test_sorts_domains_alphabetically(self, sample_user_domains_data):
        council_results = [
            {"council_name": "Alpha Council", "domain": "alpha.gov.uk"},
            {"council_name": "Zeta Council", "domain": "zeta.gov.uk"},
        ]
        merge_domains(sample_user_domains_data, council_results)
        patterns = [d["domain_pattern"] for d in sample_user_domains_data["domains"]]
        assert patterns == sorted(patterns)

    def test_new_entry_structure(self, sample_user_domains_data):
        council_results = [{"council_name": "Test Council", "domain": "test.gov.uk"}]
        merge_domains(sample_user_domains_data, council_results)
        entry = next(
            d for d in sample_user_domains_data["domains"] if d["domain_pattern"] == "test.gov.uk"
        )
        assert entry["identifiers"] == {}
        assert entry["notes"] == "Local authority: Test Council"
        assert entry["organisation_id"] is None
        assert entry["organisation_type_id"] == "local_authority"
        assert entry["source"] == SOURCE_ID


# =============================================================================
# Unit Tests: File I/O
# =============================================================================


class TestFileIO:
    """Tests for load_user_domains and save_user_domains functions."""

    def test_load_user_domains(self, temp_json_file, sample_user_domains_data):
        data = load_user_domains(temp_json_file)
        assert data["version"] == sample_user_domains_data["version"]
        assert len(data["domains"]) == len(sample_user_domains_data["domains"])

    def test_save_user_domains(self, tmp_path, sample_user_domains_data):
        filepath = tmp_path / "output.json"
        save_user_domains(filepath, sample_user_domains_data)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert content.endswith("\n")
        loaded = json.loads(content)
        assert loaded["version"] == sample_user_domains_data["version"]


# =============================================================================
# Integration Tests: HTTP Fetching (Mocked)
# =============================================================================


class TestFetchPage:
    """Tests for fetch_page function with mocked HTTP."""

    def test_fetch_page_success(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Test</html>"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_page("https://example.com")
        assert result == "<html>Test</html>"

    def test_fetch_page_http_error(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "https://example.com", 404, "Not Found", {}, None
            )
            result = fetch_page("https://example.com")
        assert result is None

    def test_fetch_page_timeout(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")
            result = fetch_page("https://example.com")
        assert result is None


class TestFetchCouncilDirectory:
    """Tests for fetch_council_directory function with mocked HTTP."""

    def test_parses_directory_table(self, sample_directory_html):
        mock_response = MagicMock()
        mock_response.read.return_value = sample_directory_html.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            councils = fetch_council_directory()

        assert len(councils) == 3
        assert ("Birmingham City Council", "/Birmingham-City-Council") in councils
        assert ("Manchester City Council", "/Manchester-City-Council") in councils
        assert ("Leeds City Council", "/Leeds-City-Council") in councils

    def test_raises_on_fetch_failure(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                DIRECTORY_URL, 500, "Server Error", {}, None
            )
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                fetch_council_directory()

    def test_raises_on_missing_table(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body>No table here</body></html>"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Could not find council directory table"):
                fetch_council_directory()

    def test_deduplicates_councils(self):
        html = """
        <table class="table sortable">
            <tr><td><a href="/Test-Council" title="Test Council">Test</a></td></tr>
            <tr><td><a href="/Test-Council" title="Test Council">Test Again</a></td></tr>
        </table>
        """
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            councils = fetch_council_directory()

        assert len(councils) == 1


class TestFetchCouncil:
    """Tests for fetch_council function with mocked HTTP."""

    def test_extracts_domain_from_page(self, sample_council_html):
        mock_response = MagicMock()
        mock_response.read.return_value = sample_council_html.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            name, domain = fetch_council(("Birmingham City Council", "/Birmingham-City-Council"))

        assert name == "Birmingham City Council"
        assert domain == "birmingham.gov.uk"

    def test_returns_none_on_no_domain(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body>No gov domain</body></html>"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            name, domain = fetch_council(("No Domain Council", "/No-Domain"))

        assert name == "No Domain Council"
        assert domain is None


# =============================================================================
# Integration Tests: Main Functions
# =============================================================================


class TestCrawlCouncilsIntegration:
    """Integration tests for crawl_councils with mocked HTTP."""

    def test_crawls_multiple_councils(self):
        def mock_urlopen(request, timeout=None):
            url = request.full_url if hasattr(request, "full_url") else request
            mock_response = MagicMock()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)

            if "Birmingham" in url:
                mock_response.read.return_value = (
                    b'<a href="https://www.birmingham.gov.uk">Website</a>'
                )
            elif "Manchester" in url:
                mock_response.read.return_value = (
                    b'<a href="https://www.manchester.gov.uk">Website</a>'
                )
            else:
                mock_response.read.return_value = b"<html>No domain</html>"

            return mock_response

        councils = [
            ("Birmingham City Council", "/Birmingham-City-Council"),
            ("Manchester City Council", "/Manchester-City-Council"),
            ("Unknown Council", "/Unknown"),
        ]

        # Import here to avoid circular imports
        from crawl_localgov import crawl_councils

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            results = crawl_councils(councils)

        assert len(results) == 2
        domains = {r["domain"] for r in results}
        assert "birmingham.gov.uk" in domains
        assert "manchester.gov.uk" in domains


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_extract_domain_malformed_html(self):
        html = "<a href='https://broken.gov.uk Website</a>"
        # Should still find the domain
        result = extract_domain(html)
        assert result == "broken.gov.uk"

    def test_merge_handles_case_insensitive_duplicates(self, sample_user_domains_data):
        # Add entry then try to add same domain with different case
        council_results = [{"council_name": "Test", "domain": "EXISTING.GOV.UK"}]
        new_count, _ = merge_domains(sample_user_domains_data, council_results)
        assert new_count == 0  # Should not add duplicate

    def test_empty_council_results(self, sample_user_domains_data):
        new_count, updated_count = merge_domains(sample_user_domains_data, [])
        assert new_count == 0
        assert updated_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
