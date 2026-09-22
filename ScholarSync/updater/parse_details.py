import json
import os
import re


ACADEMIC_YEAR = "2026-27"


def get_base_dir():
    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


def load_scholarships():
    base_dir = get_base_dir()

    path = os.path.join(
        base_dir,
        "data",
        "scholarships.json"
    )

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return data.get("scholarships", [])

    return data


def read_text(index):
    base_dir = get_base_dir()

    path = os.path.join(
        base_dir,
        "data",
        "pdf_text",
        f"{index:02d}_scholarship.txt"
    )

    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


# ---------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------

def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def get_sections(text):
    """
    Scholarship PDFs usually contain sections such as:
    Eligibility, Conditions, Income, Documents, etc.

    We keep only relevant portions instead of searching
    the complete PDF blindly.
    """

    text = clean_text(text)

    keywords = [
        "eligibility",
        "eligibility criteria",
        "conditions",
        "income",
        "academic",
        "qualification",
        "educational qualification",
        "selection",
        "documents",
        "who can apply"
    ]

    sections = []

    lines = text.splitlines()

    for i, line in enumerate(lines):

        lower = line.lower().strip()

        if any(keyword in lower for keyword in keywords):

            start = max(0, i - 2)
            end = min(len(lines), i + 35)

            section = "\n".join(
                lines[start:end]
            )

            sections.append(section)

    return "\n".join(sections)


def context_windows(text, keywords, window=800):
    """
    Returns text around important keywords.
    """

    results = []

    lower = text.lower()

    for keyword in keywords:

        start = 0

        while True:

            position = lower.find(
                keyword.lower(),
                start
            )

            if position == -1:
                break

            left = max(
                0,
                position - window
            )

            right = min(
                len(text),
                position + len(keyword) + window
            )

            results.append(
                text[left:right]
            )

            start = position + len(keyword)

    return results


# ---------------------------------------------------------
# INCOME
# ---------------------------------------------------------

def parse_money(value):
    value = value.lower()
    value = value.replace(",", "")
    value = value.replace("₹", "")
    value = value.replace("rs.", "")
    value = value.replace("rs", "")
    value = value.strip()

    match = re.search(
        r"(\d+(?:\.\d+)?)",
        value
    )

    if not match:
        return None

    number = float(match.group(1))

    if "crore" in value:
        number *= 10000000

    elif "lakh" in value or "lac" in value:
        number *= 100000

    elif "thousand" in value:
        number *= 1000

    return int(number)


def find_income(text):
    """
    Only accept numbers that are directly connected
    to family/annual income statements.
    """

    relevant = context_windows(
        text,
        [
            "annual family income",
            "family income",
            "annual income",
            "parental income",
            "parent's income",
            "parents income",
            "income of family",
            "income limit"
        ],
        window=300
    )

    patterns = [

        r"(?:annual family income|family income)"
        r".{0,100}?"
        r"(?:Rs\.?|₹|INR)?\s*"
        r"([\d,.]+\s*(?:lakh|lac|crore)?)",

        r"(?:income limit|annual income)"
        r".{0,100}?"
        r"(?:Rs\.?|₹|INR)?\s*"
        r"([\d,.]+\s*(?:lakh|lac|crore)?)",

        r"(?:income of family)"
        r".{0,100}?"
        r"(?:Rs\.?|₹|INR)?\s*"
        r"([\d,.]+\s*(?:lakh|lac|crore)?)"
    ]

    for section in relevant:

        for pattern in patterns:

            match = re.search(
                pattern,
                section,
                re.IGNORECASE |
                re.DOTALL
            )

            if match:

                value = parse_money(
                    match.group(1)
                )

                # Ignore suspicious tiny numbers
                # such as page numbers / list numbers.
                if value is not None and value >= 10000:
                    return value, match.group(0)

    return None, ""


# ---------------------------------------------------------
# PERCENTAGE
# ---------------------------------------------------------

def find_percentage(text):

    relevant = context_windows(
        text,
        [
            "minimum marks",
            "minimum percentage",
            "minimum academic",
            "academic qualification",
            "percentage of marks",
            "marks obtained",
            "at least"
        ],
        window=400
    )

    patterns = [

        r"(?:minimum percentage|minimum marks)"
        r".{0,150}?"
        r"(\d{2}(?:\.\d+)?)\s*%",

        r"(?:at least)"
        r".{0,100}?"
        r"(\d{2}(?:\.\d+)?)\s*%",

        r"(\d{2}(?:\.\d+)?)\s*%"
        r".{0,100}?(?:marks|academic|qualification)"
    ]

    candidates = []

    for section in relevant:

        for pattern in patterns:

            matches = re.finditer(
                pattern,
                section,
                re.IGNORECASE |
                re.DOTALL
            )

            for match in matches:

                try:
                    value = float(
                        match.group(1)
                    )

                    if 30 <= value <= 100:
                        candidates.append(
                            (value, match.group(0))
                        )

                except ValueError:
                    pass

    if candidates:
        value, evidence = candidates[0]

        if value.is_integer():
            value = int(value)

        return value, evidence

    return None, ""


# ---------------------------------------------------------
# CATEGORY
# ---------------------------------------------------------

def detect_categories(text):

    relevant = context_windows(
        text,
        [
            "eligible students",
            "eligible candidates",
            "eligibility",
            "category",
            "belonging to"
        ],
        window=500
    )

    combined = "\n".join(relevant).lower()

    categories = []

    category_patterns = {

        "SC": [
            r"\bSC\b",
            r"scheduled caste"
        ],

        "ST": [
            r"\bST\b",
            r"scheduled tribe"
        ],

        "OBC": [
            r"\bOBC\b",
            r"other backward classes"
        ],

        "EWS": [
            r"\bEWS\b",
            r"economically weaker section"
        ],

        "EBC": [
            r"\bEBC\b",
            r"economically backward class"
        ],

        "DNT": [
            r"\bDNT\b",
            r"denotified tribes"
        ]
    }

    for category, patterns in category_patterns.items():

        for pattern in patterns:

            if re.search(
                pattern,
                combined,
                re.IGNORECASE
            ):
                categories.append(category)
                break

    return categories, combined[:1500]


# ---------------------------------------------------------
# GENDER
# ---------------------------------------------------------

def detect_gender(text):

    relevant = context_windows(
        text,
        [
            "only girl",
            "girl students",
            "female students",
            "male students",
            "boys only",
            "girls only",
            "women candidates",
            "women students"
        ],
        window=250
    )

    combined = "\n".join(
        relevant
    ).lower()

    # Strong phrases only.
    # Merely mentioning women's reservation
    # must NOT make the entire scheme Female.

    female_patterns = [
        r"only\s+(?:girl|female|women)",
        r"girls?\s+only",
        r"female\s+students?\s+only",
        r"women\s+(?:students?|candidates?)\s+only"
    ]

    male_patterns = [
        r"only\s+(?:boy|male|men)",
        r"boys?\s+only",
        r"male\s+students?\s+only",
        r"men\s+(?:students?|candidates?)\s+only"
    ]

    for pattern in female_patterns:

        if re.search(
            pattern,
            combined,
            re.IGNORECASE
        ):
            return "Female", combined[:1000]

    for pattern in male_patterns:

        if re.search(
            pattern,
            combined,
            re.IGNORECASE
        ):
            return "Male", combined[:1000]

    return "All", ""


# ---------------------------------------------------------
# DISABILITY
# ---------------------------------------------------------

def detect_disability(text):

    name_and_eligibility = text.lower()

    strong_terms = [
        "students with disabilities",
        "student with disability",
        "specially abled students",
        "specially abled student",
        "persons with disabilities",
        "person with disability",
        "benchmark disability"
    ]

    for term in strong_terms:

        if term in name_and_eligibility:
            return True, term

    return False, ""


def find_disability_percentage(text):

    relevant = context_windows(
        text,
        [
            "disability",
            "benchmark disability",
            "percentage disability"
        ],
        window=250
    )

    patterns = [
        r"(\d{2})\s*%\s*(?:or more)?\s*disabil",
        r"disabil\w*.{0,100}?(\d{2})\s*%"
    ]

    for section in relevant:

        for pattern in patterns:

            match = re.search(
                pattern,
                section,
                re.IGNORECASE |
                re.DOTALL
            )

            if match:

                value = int(
                    match.group(1)
                )

                if 1 <= value <= 100:
                    return value, match.group(0)

    return None, ""


# ---------------------------------------------------------
# COURSE
# ---------------------------------------------------------

def detect_courses(text):

    relevant = context_windows(
        text,
        [
            "eligible courses",
            "course",
            "degree",
            "programme",
            "program",
            "studies"
        ],
        window=350
    )

    combined = "\n".join(
        relevant
    ).lower()

    courses = []

    course_patterns = {

        "B.Tech": [
            r"\bb\.?\s*tech\b",
            r"bachelor of technology"
        ],

        "B.E.": [
            r"\bb\.?\s*e\.?\b",
            r"bachelor of engineering"
        ],

        "Diploma": [
            r"\bdiploma\b"
        ],

        "UG": [
            r"\bundergraduate\b"
        ],

        "PG": [
            r"\bpostgraduate\b",
            r"\bpost graduate\b"
        ],

        "PhD": [
            r"\bph\.?\s*d\.?\b",
            r"doctoral"
        ]
    }

    for course, patterns in course_patterns.items():

        for pattern in patterns:

            if re.search(
                pattern,
                combined,
                re.IGNORECASE
            ):

                courses.append(course)
                break

    return courses, combined[:1500]


# ---------------------------------------------------------
# BENEFIT
# ---------------------------------------------------------

def find_benefit(text):

    relevant = context_windows(
        text,
        [
            "scholarship amount",
            "scholarship will be",
            "financial assistance",
            "amount of scholarship",
            "rate of scholarship",
            "scholarship at the rate"
        ],
        window=350
    )

    patterns = [
        r"(?:scholarship amount|amount of scholarship)"
        r".{0,150}?"
        r"(?:Rs\.?|₹|INR)\s*([\d,]+)",

        r"(?:scholarship will be|financial assistance)"
        r".{0,150}?"
        r"(?:Rs\.?|₹|INR)\s*([\d,]+)",

        r"(?:at the rate of|rate of scholarship)"
        r".{0,150}?"
        r"(?:Rs\.?|₹|INR)\s*([\d,]+)"
    ]

    for section in relevant:

        for pattern in patterns:

            match = re.search(
                pattern,
                section,
                re.IGNORECASE |
                re.DOTALL
            )

            if match:

                value = int(
                    match.group(1).replace(",", "")
                )

                if value >= 100:
                    return value, match.group(0)

    return None, ""


# ---------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------

def find_documents(text):

    relevant = context_windows(
        text,
        [
            "documents required",
            "required documents",
            "documents to be uploaded",
            "following documents",
            "documents"
        ],
        window=1000
    )

    documents = []

    document_patterns = [
        r"10th.*?marksheet",
        r"12th.*?marksheet",
        r"10\+2.*?marksheet",
        r"income certificate",
        r"caste certificate",
        r"domicile certificate",
        r"disability certificate",
        r"bonafide certificate",
        r"bank account",
        r"aadhaar",
        r"death certificate"
    ]

    combined = "\n".join(
        relevant
    )

    for pattern in document_patterns:

        match = re.search(
            pattern,
            combined,
            re.IGNORECASE
        )

        if match:

            value = match.group(0).strip()

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            documents.append(value)

    return list(
        dict.fromkeys(documents)
    )


# ---------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------

def parse_scholarship(
    scholarship,
    index
):

    text = read_text(index)

    if len(text.strip()) < 100:

        print(
            f"  WARNING: text too short"
        )

        return {
            "id": f"SCH{index:03d}",

            "name": scholarship["name"],

            "provider": None,

            "source": {
                "portal": "NSP",
                "url": scholarship.get("url"),
                "last_verified": None
            },

            "academic_year": ACADEMIC_YEAR,

            "classification": {
                "type": (
                    "merit_based"
                    if "merit based" in
                    scholarship["name"].lower()
                    else
                    "welfare_based"
                    if "welfare based" in
                    scholarship["name"].lower()
                    else None
                )
            },

            "eligibility": {
                "income_limit": None,
                "category": [],
                "course": [],
                "min_academic_percentage": None,
                "gender": "All",
                "state_domicile": "All India",
                "disability_required": None,
                "minimum_disability_percentage": None
            },

            "benefit_amount": None,

            "required_documents": [],

            "deadline": None,

            "conflict_rules": {
                "cannot_combine_with": [],
                "can_combine_with": []
            },

            "evidence": {},

            "raw_text_file":
                f"pdf_text/{index:02d}_scholarship.txt"
        }

    text = clean_text(text)

    eligibility_text = get_sections(text)

    # Income
    income, income_evidence = find_income(
        eligibility_text
    )

    # Percentage
    percentage, percentage_evidence = find_percentage(
        eligibility_text
    )

    # Category
    categories, category_evidence = detect_categories(
        eligibility_text
    )

    # Gender
    gender, gender_evidence = detect_gender(
        eligibility_text
    )

    # Disability
    disability, disability_evidence = detect_disability(
        text
    )

    disability_percentage, disability_percentage_evidence = \
        find_disability_percentage(
            eligibility_text
        )

    # Course
    courses, course_evidence = detect_courses(
        eligibility_text
    )

    # Benefit
    benefit, benefit_evidence = find_benefit(
        text
    )

    # Documents
    documents = find_documents(
        text
    )

    return {

        "id": f"SCH{index:03d}",

        "name": scholarship["name"],

        "provider": None,

        "source": {
            "portal": "NSP",
            "url": scholarship.get("url"),
            "last_verified": None
        },

        "academic_year": ACADEMIC_YEAR,

        "classification": {
            "type": (
                "merit_based"
                if "merit based" in
                scholarship["name"].lower()
                else
                "welfare_based"
                if "welfare based" in
                scholarship["name"].lower()
                else None
            )
        },

        "eligibility": {

            "income_limit": income,

            "category": categories,

            "course": courses,

            "min_academic_percentage":
                percentage,

            "gender": gender,

            "state_domicile":
                "All India",

            "disability_required":
                disability,

            "minimum_disability_percentage":
                disability_percentage
        },

        "benefit_amount":
            benefit,

        "required_documents":
            documents,

        "deadline":
            None,

        "conflict_rules": {

            "cannot_combine_with": [],

            "can_combine_with": []
        },

        "evidence": {

            "income":
                income_evidence,

            "percentage":
                percentage_evidence,

            "category":
                category_evidence,

            "course":
                course_evidence,

            "gender":
                gender_evidence,

            "disability":
                disability_evidence,

            "disability_percentage":
                disability_percentage_evidence,

            "benefit":
                benefit_evidence,

            "documents":
                documents
        },

        "raw_text_file":
            f"pdf_text/{index:02d}_scholarship.txt"
    }


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    scholarships = load_scholarships()

    print(
        f"Scholarships found: {len(scholarships)}"
    )

    detailed = []

    for index, scholarship in enumerate(
        scholarships,
        start=1
    ):

        print(
            f"\n[{index}] "
            f"{scholarship['name']}"
        )

        result = parse_scholarship(
            scholarship,
            index
        )

        detailed.append(result)

        print(
            "  Income:",
            result["eligibility"]["income_limit"]
        )

        print(
            "  Percentage:",
            result["eligibility"]
            ["min_academic_percentage"]
        )

        print(
            "  Category:",
            result["eligibility"]["category"]
        )

        print(
            "  Course:",
            result["eligibility"]["course"]
        )

        print(
            "  Gender:",
            result["eligibility"]["gender"]
        )

        print(
            "  Disability:",
            result["eligibility"]
            ["disability_required"]
        )

        print(
            "  Benefit:",
            result["benefit_amount"]
        )

    base_dir = get_base_dir()

    output_path = os.path.join(
        base_dir,
        "data",
        "scholarships_detailed_v3.json"
    )

    output = {

        "metadata": {

            "academic_year":
                ACADEMIC_YEAR,

            "source":
                "NSP",

            "description":
                "Context-aware scholarship "
                "data extracted from official "
                "NSP scholarship documents"
        },

        "scholarships":
            detailed
    }

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        "\n================================"
    )

    print(
        "DONE"
    )

    print(
        f"Output: {output_path}"
    )


if __name__ == "__main__":
    main()