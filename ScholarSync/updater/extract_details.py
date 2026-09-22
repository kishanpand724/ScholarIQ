import requests
import json
import os
import time
from io import BytesIO
from pypdf import PdfReader


def get_base_dir():
    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


def extract_pdf_text(pdf_url, retries=3):

    if not pdf_url or pdf_url.endswith("/null"):
        return ""

    for attempt in range(1, retries + 1):

        try:
            print(f"  Download attempt {attempt}/{retries}")

            response = requests.get(
                pdf_url,
                timeout=120,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            if len(response.content) < 1000:
                raise Exception("PDF download too small")

            reader = PdfReader(
                BytesIO(response.content)
            )

            pages = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pages.append(text)

            final_text = "\n".join(pages).strip()

            if final_text:
                return final_text

            print("  PDF downloaded but no text found.")

        except Exception as error:

            print(f"  PDF error: {error}")

        if attempt < retries:
            print("  Retrying...")
            time.sleep(3)

    return ""


def clean_text(text):

    text = text.replace("\r", "\n")

    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def load_data():

    base_dir = get_base_dir()

    input_path = os.path.join(
        base_dir,
        "data",
        "scholarships.json"
    )

    with open(
        input_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_failed(failed):

    base_dir = get_base_dir()

    output_path = os.path.join(
        base_dir,
        "data",
        "failed_pdfs.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            failed,
            file,
            indent=2,
            ensure_ascii=False
        )


def process_scholarships(data):

    base_dir = get_base_dir()

    output_dir = os.path.join(
        base_dir,
        "data",
        "pdf_text"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    failed = []

    total = len(data["scholarships"])

    for index, scholarship in enumerate(
        data["scholarships"],
        start=1
    ):

        name = scholarship["name"]
        url = scholarship["url"]

        filename = f"{index:02d}_scholarship.txt"

        output_path = os.path.join(
            output_dir,
            filename
        )

        print(f"\n[{index}/{total}] {name}")

        # Already successfully extracted
        if os.path.exists(output_path):

            with open(
                output_path,
                "r",
                encoding="utf-8"
            ) as file:

                existing_text = file.read().strip()

            if len(existing_text) > 100:

                print(
                    f"  Already extracted "
                    f"({len(existing_text)} characters). Skipping."
                )

                continue

        text = extract_pdf_text(url)

        text = clean_text(text)

        if text:

            with open(
                output_path,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(text)

            print(
                f"  Extracted characters: "
                f"{len(text)}"
            )

        else:

            print("  FAILED")

            failed.append({
                "name": name,
                "url": url,
                "file": filename
            })

    save_failed(failed)

    print("\nPDF extraction complete.")
    print(f"Failed PDFs: {len(failed)}")


if __name__ == "__main__":

    data = load_data()

    process_scholarships(data)