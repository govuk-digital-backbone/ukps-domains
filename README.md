# ukps-domains

A public, machine-readable list of UK public sector domains used for user identities and email, published in JSON with supporting schemas.

- [user_domains.json](data/user_domains.json)

> [!CAUTION]
> This repository is a work in progress and may not contain a complete or accurate list of all UK public sector domains. The format and structure of JSON files are likely not finalised.

## Purpose

This list focuses on organisational domains - the domains people use for email and identity.  
Service, product, and campaign subdomains aren't included.

If you need to validate the affiliation of an email address, extract its domain (the part after @). If that domain (case-insensitive) matches an entry in the `user_domains` list, you can treat the address as belonging to a UK public sector organisation. You can then use the record to retrieve metadata for enrichment, profiling, or access control.

> **_NOTE:_** This is for affiliation checks, not individual user verification.

## Definition

This repository follows the [Office for National Statistics (ONS) classification](https://www.ons.gov.uk/methodology/classificationsandstandards/economicstatisticsclassifications/introductiontoeconomicstatisticsclassifications) of the UK public sector, defined as general government units plus public corporations:

- **Central government**: Non-market producers with national or UK-wide geographic remit
- **Local government**: Non-market producers with local geographic remit (county or group of counties)
- **Public corporations**: Market producers under public sector control

Control indicators include board appointment rights, voting interest ownership, special shares, and contractual arrangements.

> **_NOTE:_** Organisations on the boundary of this definition may require case-by-case assessment. See [Discussions](https://github.com/orgs/govuk-digital-backbone/discussions/categories/domains-and-identifiers) for edge cases.

## Scope

Covers domains for:

- Central government
- Local authorities
- NHS and health bodies
- Emergency services
- NDPBs and ALBs
- Devolved administrations

> **_NOTE:_** If an organisation already publishes authoritative domain data, this repo will reference that source instead.

## Adding or Updating Domains

If you'd like to propose a change:

- Open an Issue (preferred) with the domain and organisation details, or
- Submit a PR directly using the template.

[Discussions](https://github.com/orgs/govuk-digital-backbone/discussions/categories/domains-and-identifiers) are available for queries or edge cases.

## Scripts

### Local Authority Crawler

The `bin/crawl_localgov.py` script crawls [localgov.co.uk/council-directory](https://www.localgov.co.uk/council-directory) to automatically extract and update local authority domains.

```bash
# Run the crawler
python bin/crawl_localgov.py

# Remove domains no longer in the directory
python bin/crawl_localgov.py --remove
```

The script:
- Fetches the council directory dynamically
- Extracts official `.gov.uk`, `.gov.scot`, `.gov.wales`, and `.llyw.cymru` domains
- Merges new domains into `data/user_domains.json`
- Updates council names if they change
- Alerts when domains are no longer in the directory
- Bumps the minor version number when changes are made

## Development

### Running Tests

```bash
pip install -r requirements-dev.txt
cd bin && python -m pytest test_crawl_localgov.py -v
```

### Linting

```bash
pip install ruff
ruff check bin/
```

Tests run automatically via GitHub Actions on pushes and PRs to `main`.
