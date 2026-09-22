import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin

NSP_URL = "https://scholarships.gov.in/All-Scholarships"


def fetch_nsp():
    response = requests.get(
        NSP_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    scholarships = []

    # Actual scholarship headings
    for heading in soup.find_all(["h5", "h6"]):

        name = heading.get_text(" ", strip=True)

        if not name:
            continue
        
        if name.lower() == "schemes on nsp":
            continue

        # Only actual scholarship/scheme names
        if "Scholarship" not in name and "Scheme" not in name:
            continue

        # Find the parent container of this scholarship
        parent = heading.parent

        if not parent:
            continue

        specification_url = None

        # Search for Specifications link inside the same container
        for link in parent.find_all("a", href=True):
            link_text = link.get_text(" ", strip=True).lower()

            if "specification" in link_text:
                specification_url = urljoin(
                    NSP_URL,
                    link["href"]
                )
                break

        scholarships.append({
            "name": name,
            "url": specification_url
        })

    # Remove duplicates
    unique_scholarships = []

    seen = set()

    for scholarship in scholarships:

        name = scholarship["name"]

        if name in seen:
            continue

        seen.add(name)
        unique_scholarships.append(scholarship)

    return unique_scholarships


def save_data(scholarships):

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    output_path = os.path.join(
        base_dir,
        "data",
        "scholarships.json"
    )

    data = {
        "metadata": {
            "academic_year": "2026-27",
            "source": "NSP",
            "last_updated": None
        },
        "scholarships": scholarships
    }

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved {len(scholarships)} scholarships")
    print(f"File: {output_path}")


if __name__ == "__main__":

    scholarships = fetch_nsp()

    save_data(scholarships)