#!/usr/bin/env python3
"""
Crawl localgov.co.uk council directory and update user_domains.json.

This script:
1. Fetches the council directory from localgov.co.uk dynamically
2. Crawls each council page to extract their official website domain
3. Validates domains are .gov.uk domains before adding
4. Merges new domains into data/user_domains.json
5. Bumps the minor version number
6. Alerts if any existing entries are no longer in the directory

Usage:
    python bin/crawl_localgov.py [--remove]

Options:
    --remove    Remove domains that are no longer in the directory
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Constants
BASE_URL = "https://www.localgov.co.uk"
DIRECTORY_URL = f"{BASE_URL}/council-directory"
SOURCE_ID = "localgov.co.uk"
USER_AGENT = "Mozilla/5.0 (compatible; UKPSDomainCrawler/1.0)"
REQUEST_TIMEOUT = 30
MAX_WORKERS = 10

# Valid government domain suffixes
VALID_SUFFIXES = (".gov.uk", ".gov.scot", ".gov.wales", ".llyw.cymru")

# Domains to skip when extracting (social media, etc.)
SKIP_DOMAINS = frozenset(["twitter.gov.uk", "youtube.gov.uk", "linkedin.gov.uk"])

# Regex pattern to extract government domains from HTML
# Matches: www.example.gov.uk, https://example.gov.uk, href="https://example.gov.uk"
DOMAIN_PATTERN = re.compile(
    r'(?:www\.|https?://(?:www\.)?|href=["\']https?://(?:www\.)?)'
    r"([a-zA-Z0-9-]+\.(?:gov\.uk|gov\.scot|gov\.wales|llyw\.cymru))",
    re.IGNORECASE,
)

# Pattern to match council links in directory table
COUNCIL_LINK_PATTERN = re.compile(
    r'href=["\'](/[A-Z][a-zA-Z0-9-]+)["\'][^>]*title="([^"]+)"'
)

# Pattern to find the council directory table
TABLE_PATTERN = re.compile(
    r'<table[^>]*class="[^"]*table[^"]*sortable[^"]*"[^>]*>.*?</table>',
    re.DOTALL,
)


def is_valid_gov_domain(domain: str) -> bool:
    """Check if domain ends with a valid government suffix."""
    return domain.lower().endswith(VALID_SUFFIXES)


def fetch_page(url: str) -> str | None:
    """Fetch a page and return its content, or None on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            return response.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} fetching {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def fetch_council_directory() -> list[tuple[str, str]]:
    """Fetch the council directory and extract all council links.

    Only extracts links from within the council directory table,
    not from navigation or other parts of the page.

    Returns:
        List of (council_name, path) tuples.

    Raises:
        RuntimeError: If the directory page or table cannot be fetched.
    """
    print(f"Fetching council directory from {DIRECTORY_URL}...", file=sys.stderr)

    html = fetch_page(DIRECTORY_URL)
    if not html:
        raise RuntimeError("Failed to fetch council directory page")

    table_match = TABLE_PATTERN.search(html)
    if not table_match:
        raise RuntimeError("Could not find council directory table in page")

    table_html = table_match.group(0)
    matches = COUNCIL_LINK_PATTERN.findall(table_html)

    # Deduplicate while preserving order
    seen_paths: set[str] = set()
    councils: list[tuple[str, str]] = []

    for path, name in matches:
        path_lower = path.lower()
        if path_lower in seen_paths:
            continue
        seen_paths.add(path_lower)

        # Clean up whitespace in name
        name = " ".join(name.split())
        if name and path:
            councils.append((name, path))

    print(f"Found {len(councils)} councils in directory table", file=sys.stderr)
    return councils


def extract_domain(html: str) -> str | None:
    """Extract the primary government domain from page HTML.

    Returns:
        The domain string, or None if no valid domain found.
    """
    if not html:
        return None

    domains: set[str] = set()

    for match in DOMAIN_PATTERN.findall(html):
        domain = match.lower()
        if domain not in SKIP_DOMAINS and is_valid_gov_domain(domain):
            domains.add(domain)

    if not domains:
        return None

    # Prefer .gov.uk domains over others
    for domain in sorted(domains):
        if domain.endswith(".gov.uk"):
            return domain
    return sorted(domains)[0]


def fetch_council(council_info: tuple[str, str]) -> tuple[str, str | None]:
    """Fetch a council page and extract its domain."""
    name, path = council_info
    url = BASE_URL + path
    html = fetch_page(url)
    domain = extract_domain(html)
    return name, domain


def crawl_councils(councils: list[tuple[str, str]]) -> list[dict]:
    """Crawl all council pages and extract domains.

    Args:
        councils: List of (council_name, path) tuples.

    Returns:
        List of dicts with 'council_name' and 'domain' keys.
    """
    print(f"Crawling {len(councils)} councils...", file=sys.stderr)

    results: list[dict] = []
    total = len(councils)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_council, c): c for c in councils}

        for i, future in enumerate(as_completed(futures), 1):
            name, domain = future.result()
            if domain:
                results.append({"council_name": name, "domain": domain})
                print(f"[{i}/{total}] {name}: {domain}", file=sys.stderr)
            else:
                print(f"[{i}/{total}] {name}: NOT FOUND", file=sys.stderr)

    return results


def load_user_domains(filepath: Path) -> dict:
    """Load the user_domains.json file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def save_user_domains(filepath: Path, data: dict) -> None:
    """Save the user_domains.json file with consistent formatting."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def find_stale_domains(data: dict, crawled_domains: set[str]) -> list[dict]:
    """Find domains with our source that are no longer in the directory.

    Args:
        data: The user_domains data structure.
        crawled_domains: Set of domains found in the current crawl.

    Returns:
        List of stale domain entries.
    """
    return [
        entry
        for entry in data["domains"]
        if entry.get("source") == SOURCE_ID
        and entry["domain_pattern"].lower() not in crawled_domains
    ]


def remove_stale_domains(data: dict, stale_domains: list[dict]) -> int:
    """Remove stale domains from user_domains data.

    Returns:
        Count of domains removed.
    """
    stale_patterns = {d["domain_pattern"].lower() for d in stale_domains}
    original_count = len(data["domains"])

    data["domains"] = [
        d for d in data["domains"] if d["domain_pattern"].lower() not in stale_patterns
    ]

    for domain in sorted(stale_patterns):
        print(f"Removed {domain}")

    return original_count - len(data["domains"])


def merge_domains(data: dict, council_results: list[dict]) -> tuple[int, int]:
    """Merge crawled council domains into the user_domains data.

    Adds new domains and updates notes for existing ones if the
    council name has changed.

    Returns:
        Tuple of (new_count, updated_count).
    """
    existing_by_domain = {d["domain_pattern"].lower(): d for d in data["domains"]}
    new_count = 0
    updated_count = 0

    for council in council_results:
        domain = council["domain"].lower()
        new_notes = f"Local authority: {council['council_name']}"

        if domain in existing_by_domain:
            existing_entry = existing_by_domain[domain]

            # Update notes if this is our entry and the name changed
            if existing_entry.get("source") == SOURCE_ID:
                old_notes = existing_entry.get("notes", "")
                if old_notes != new_notes:
                    print(f"📝 Updated {domain}: '{old_notes}' → '{new_notes}'")
                    existing_entry["notes"] = new_notes
                    updated_count += 1
            continue

        # Create new entry
        entry = {
            "domain_pattern": domain,
            "identifiers": {},
            "notes": new_notes,
            "organisation_id": None,
            "organisation_type_id": "local_authority",
            "source": SOURCE_ID,
        }

        data["domains"].append(entry)
        existing_by_domain[domain] = entry
        new_count += 1
        print(f"Added {domain}")

    # Sort domains alphabetically
    data["domains"].sort(key=lambda x: x["domain_pattern"])

    return new_count, updated_count


def bump_minor_version(version: str) -> str:
    """Bump the minor version number (e.g., 0.0.4 -> 0.1.0)."""
    major, minor, patch = version.split(".")
    return f"{major}.{int(minor) + 1}.0"


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Crawl localgov.co.uk council directory and update user_domains.json",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove domains that are no longer in the directory",
    )
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    user_domains_path = repo_root / "data" / "user_domains.json"

    # Fetch council directory
    councils = fetch_council_directory()
    if not councils:
        print("ERROR: No councils found in directory", file=sys.stderr)
        sys.exit(1)

    # Crawl council pages
    council_results = crawl_councils(councils)
    print(f"\nSuccessfully extracted {len(council_results)} domains", file=sys.stderr)

    # Build set of crawled domains for comparison
    crawled_domains = {r["domain"].lower() for r in council_results}

    # Load existing data
    data = load_user_domains(user_domains_path)
    original_count = len(data["domains"])

    # Check for stale domains
    stale_domains = find_stale_domains(data, crawled_domains)
    removed_count = 0

    if stale_domains:
        print(
            f"\n⚠️  WARNING: {len(stale_domains)} domain(s) with source "
            f"'{SOURCE_ID}' are no longer in the directory:",
            file=sys.stderr,
        )
        for entry in stale_domains:
            note = entry.get("notes", "")
            print(f"    - {entry['domain_pattern']} ({note})", file=sys.stderr)

        if args.remove:
            print("\nRemoving stale domains (--remove flag set)...", file=sys.stderr)
            removed_count = remove_stale_domains(data, stale_domains)
        else:
            print("\n   Run with --remove to delete these entries.", file=sys.stderr)

    # Merge new domains and update existing ones
    new_count, updated_count = merge_domains(data, council_results)

    # Bump version and save if we made changes
    if new_count > 0 or removed_count > 0 or updated_count > 0:
        old_version = data["version"]
        data["version"] = bump_minor_version(old_version)
        print(f"\nVersion: {old_version} -> {data['version']}")
        save_user_domains(user_domains_path, data)

    # Print summary
    print(f"\n{'=' * 50}")
    print("Summary:")
    print(f"  Councils found in directory: {len(councils)}")
    print(f"  Domains extracted: {len(council_results)}")
    print(f"  New domains added: {new_count}")
    print(f"  Domains updated: {updated_count}")
    print(f"  Stale domains found: {len(stale_domains)}")
    print(f"  Domains removed: {removed_count}")
    print(f"  Total domains: {len(data['domains'])} (was {original_count})")
    print(f"  Version: {data['version']}")


if __name__ == "__main__":
    main()
