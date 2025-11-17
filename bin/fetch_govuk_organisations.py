import requests
import json
from pathlib import Path

API_URL = "https://www.gov.uk/api/organisations?page={}"

def fetch_all_organisations():
    all_results = []
    page = 1

    while True:
        url = API_URL.format(page)
        print(f"Fetching page {page}... {url}")
        r = requests.get(url)
        r.raise_for_status()

        data = r.json()

        results = data.get("results", [])
        all_results.extend(results)

        total = data.get("total")
        start_index = data.get("start_index")
        page_size = len(results)

        if start_index + page_size - 1 >= total:
            break

        page += 1

    return all_results


def main():
    # Directory of this script (e.g. bin/)
    script_dir = Path(__file__).resolve().parent

    # repo root = one level up from bin/
    repo_root = script_dir.parent

    # Output file path inside data/
    output_file = (repo_root / "data" / "govuk_organisations.json").resolve()

    # Ensure data/ exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Fetch and write out
    results = fetch_all_organisations()

    output_file.write_text(
        json.dumps(results, indent=4),
        encoding="utf-8"
    )

    print(f"Saved {len(results)} organisations to {output_file}")


if __name__ == "__main__":
    main()
