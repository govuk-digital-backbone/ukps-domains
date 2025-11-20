#!/usr/bin/env python3

import json
from collections import OrderedDict
from pathlib import Path

def sort_keys(obj):
    """Return an OrderedDict with keys sorted alphabetically."""
    return OrderedDict(sorted(obj.items(), key=lambda x: x[0]))

def main():
    # Path to this script
    script_dir = Path(__file__).resolve().parent

    # Resolve ../data/user_domains.json relative to the script location
    input_file = (script_dir / ".." / "data" / "user_domains.json").resolve()

    # Read original raw text
    original_text = input_file.read_text(encoding="utf-8")

    # Parse JSON
    data = json.loads(original_text)

    domains = data.get("domains", [])

    # Sort list and keys
    domains_sorted = sorted(domains, key=lambda x: x.get("domain_pattern", ""))
    domains_sorted = [sort_keys(entry) for entry in domains_sorted]

    data["domains"] = domains_sorted

    # Create new formatted text
    new_text = json.dumps(data, indent=4, ensure_ascii=False)

    # Add final newline
    new_text += "\n"

    # Only write if different
    if new_text != original_text:
        input_file.write_text(new_text, encoding="utf-8")
        print("Formatted and saved: changes detected.")
    else:
        print("No changes needed: file already formatted.")

if __name__ == "__main__":
    main()
