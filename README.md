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
