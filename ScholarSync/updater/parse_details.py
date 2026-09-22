from __future__ import annotations

import json
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import date
from typing import Optional


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SOURCE_FILE = DATA / "scholarships.json"
TEXT_DIR = DATA / "pdf_text"
OUTPUT_FILE = DATA / "scholarships_detailed.json"

PARSER_VERSION = "FINAL-1.0"
TODAY = date.today().isoformat()


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\u00a0", " ")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("−", "-")
    text = text.replace("’", "'")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def lower(text: str) -> str:
    return clean(text).lower()


def evidence(text: str, limit: int = 500) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def unique(values):
    result = []
    seen = set()

    for value in values:
        key = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False
        ) if isinstance(value, (dict, list)) else value

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


# ============================================================
# JSON
# ============================================================

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def get_scholarships():
    data = load_json(SOURCE_FILE)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in (
            "scholarships",
            "data",
            "results",
            "items"
        ):
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError(
        "scholarships.json ka structure samajh nahi aaya."
    )


# ============================================================
# TEXT FILE
# ============================================================

def get_text_file(entry, index: int):

    raw = entry.get("raw_text_file")

    if raw:
        path = DATA / raw

        if path.exists():
            return path

    candidates = [
        TEXT_DIR / f"{index:02d}_scholarship.txt",
        TEXT_DIR / f"{index}_scholarship.txt",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def load_text(entry, index):

    path = get_text_file(entry, index)

    if not path:
        return "", None

    text = path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    return clean(text), path


# ============================================================
# SECTION DETECTION
# ============================================================

SECTION_PATTERNS = {

    "eligibility": [
        r"^\s*eligibility\s*$",
        r"eligibility criteria",
        r"eligibility conditions",
        r"conditions of eligibility",
        r"who can apply",
    ],

    "exclusion": [
        r"not eligible",
        r"categories.*not eligible",
        r"exclusion",
        r"ineligible",
    ],

    "documents": [
        r"documents required",
        r"documents to be uploaded",
        r"list of documents",
        r"supporting documents",
        r"documents/certificates",
    ],

    "benefit": [
        r"amount of scholarship",
        r"rate of scholarship",
        r"scholarship amount",
        r"quantum of scholarship",
        r"scholarship rates",
        r"amount payable",
    ],

    "reservation": [
        r"reservation",
        r"reserved seats",
        r"horizontal reservation",
        r"vertical reservation",
        r"earmarked",
        r"quota",
    ],

    "selection": [
        r"selection criteria",
        r"selection process",
        r"merit list",
        r"ranking",
        r"tie.?breaking",
    ],

    "conflict": [
        r"other scholarship",
        r"other financial assistance",
        r"cannot avail",
        r"not availing",
    ]
}


def detect_section(line):

    l = lower(line)

    for section, patterns in SECTION_PATTERNS.items():

        for pattern in patterns:

            if re.search(pattern, l):
                return section

    return None


@dataclass
class Unit:

    text: str
    section: str
    number: int


def make_units(text):

    lines = text.splitlines()

    units = []

    section = "general"

    buffer = ""

    def flush():

        nonlocal buffer

        if not buffer.strip():
            return

        value = clean(buffer)

        # Split obvious numbered statements.
        parts = re.split(
            r"(?<=[.;:])\s+"
            r"(?=(?:\(?[ivx]+\)?|\(?\d+\)?|[-•]))",
            value,
            flags=re.I
        )

        for part in parts:

            part = clean(part)

            if part:

                units.append(
                    Unit(
                        part,
                        section,
                        len(units)
                    )
                )

        buffer = ""

    for raw in lines:

        line = clean(raw)

        if not line:
            flush()
            continue

        if re.match(
            r"^\[(?:PAGE|SOURCE_URL|FINAL_URL|PDF_SHA256|EXTRACTED_AT)",
            line,
            re.I
        ):
            flush()
            continue

        new_section = detect_section(line)

        if new_section:

            flush()
            section = new_section
            continue

        if buffer:
            buffer += " " + line
        else:
            buffer = line

        if len(buffer) > 1000:
            flush()

    flush()

    return units


# ============================================================
# CONTEXT
# ============================================================

def is_negative(text):

    l = lower(text)

    patterns = [
        r"\bnot eligible\b",
        r"\bshall not be eligible\b",
        r"\bwill not be eligible\b",
        r"\bineligible\b",
        r"\bnot entitled\b",
        r"\bnot allowed\b",
        r"\bnot permitted\b",
        r"\bexcluded\b",
        r"\bexclusion\b",
    ]

    return any(
        re.search(p, l)
        for p in patterns
    )


def is_reservation(text):

    l = lower(text)

    return bool(
        re.search(
            r"\breservation\b"
            r"|\breserved\b"
            r"|\bquota\b"
            r"|\bearmarked\b"
            r"|\bhorizontal\b"
            r"|\bvertical\b"
            r"|\bseats?\b.{0,30}\breserved\b",
            l
        )
    )


def is_document_context(text):

    l = lower(text)

    return bool(
        re.search(
            r"\bsubmit\b.{0,100}"
            r"(certificate|document|proof|marksheet)",
            l
        )
        or
        re.search(
            r"\bupload\b.{0,100}"
            r"(certificate|document|proof|marksheet)",
            l
        )
        or
        re.search(
            r"\benclose\b.{0,100}"
            r"(certificate|document|proof)",
            l
        )
    )


def is_example(text):

    return bool(
        re.search(
            r"\b(like|such as|for example|e\.g\.|including)\b",
            lower(text)
        )
    )


def eligibility_sentence(text):

    return bool(
        re.search(
            r"\b("
            r"eligible|eligibility|"
            r"candidate.*should|"
            r"student.*should|"
            r"candidate.*must|"
            r"student.*must|"
            r"belonging to|"
            r"pursuing|"
            r"enrolled|"
            r"admitted|"
            r"family income|"
            r"domicile"
            r")\b",
            lower(text)
        )
    )


def field_units(units, field):

    score = {
        "eligibility": 40,
        "exclusion": 20,
        "documents": 5,
        "benefit": 35,
        "general": 0,
        "reservation": 0,
        "selection": 0,
        "conflict": 35,
    }

    result = []

    for u in units:

        result.append(
            (
                u.text,
                u.section,
                score.get(u.section, 0)
            )
        )

    return result


# ============================================================
# SCHEME NAME HINTS
# ============================================================

def hints(name):

    l = lower(name)

    return {

        "girl":
            bool(
                re.search(
                    r"girl students?|female students?",
                    l
                )
            ),

        "disability":
            bool(
                re.search(
                    r"special(?:ly)? abled|"
                    r"students? with disabilities|"
                    r"students? with disability",
                    l
                )
            ),

        "degree":
            "technical degree" in l,

        "diploma":
            "technical diploma" in l,

        "pre_matric":
            "pre matric" in l,

        "post_matric":
            "post matric" in l,

        "nmmss":
            "national means cum merit" in l,

        "jkl":
            bool(
                re.search(
                    r"jammu.*kashmir|ladakh",
                    l
                )
            ),

        "ner":
            bool(
                re.search(
                    r"north eastern|north-east|\bner\b",
                    l
                )
            ),

        "sc":
            bool(
                re.search(
                    r"\bsc students?\b|"
                    r"top class.*sc",
                    l
                )
            ),

        "st":
            bool(
                re.search(
                    r"\bst students?\b|"
                    r"higher education of st|"
                    r"schedule tribe",
                    l
                )
            ),

        "obc":
            bool(
                re.search(
                    r"\bobc\b|\bebc\b|\bdnt\b",
                    l
                )
            )
    }


# ============================================================
# MONEY
# ============================================================

def parse_money(raw):

    value = lower(raw)

    value = value.replace(",", "")

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(crore|cr|lakh|lac|lakhs|lacs)\b",
        value
    )

    if match:

        number = float(match.group(1))
        unit = match.group(2)

        if unit in ("crore", "cr"):
            return int(number * 10_000_000)

        return int(number * 100_000)

    # Plain currency numbers.
    match = re.search(
        r"\b(\d{4,9})\b",
        value
    )

    if match:
        return int(match.group(1))

    return None


def money_mentions(text):

    patterns = [

        r"(?:rs\.?|inr|₹)\s*"
        r"\d[\d,]*(?:\.\d+)?"
        r"(?:\s*(?:lakh|lac|crore|cr))?",

        r"\d+(?:\.\d+)?\s*"
        r"(?:lakh|lac|lakhs|lacs|crore|cr)\b"
    ]

    result = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            re.I
        ):

            raw = match.group(0)

            value = parse_money(raw)

            if value is not None:
                result.append(
                    (
                        value,
                        raw
                    )
                )

    return unique(result)


# ============================================================
# INCOME
# ============================================================

INCOME_PATTERNS = [

    r"family income.{0,100}"
    r"(?:not more than|not exceed|does not exceed|"
    r"shall not exceed|less than|below|upto|up to)",

    r"income from all sources.{0,100}"
    r"(?:not more than|not exceed|less than|below|upto|up to)",

    r"annual income.{0,100}"
    r"(?:not more than|not exceed|less than|below|upto|up to)",

    r"parents?.{0,60}income.{0,100}"
    r"(?:not more than|not exceed|less than|below|upto|up to)"
]


def extract_income(units):

    candidates = []

    for text, section, score in field_units(
        units,
        "income"
    ):

        if is_negative(text):
            continue

        if is_document_context(text):
            continue

        l = lower(text)

        if not any(
            re.search(pattern, l)
            for pattern in INCOME_PATTERNS
        ):
            continue

        amounts = money_mentions(text)

        for value, raw in amounts:

            points = score + 30

            if "per annum" in l:
                points += 10

            if "family income" in l:
                points += 10

            candidates.append(
                (
                    points,
                    value,
                    text
                )
            )

    if not candidates:
        return None, "", 0.0

    candidates.sort(
        reverse=True
    )

    top_score = candidates[0][0]

    values = {
        value
        for score, value, text
        in candidates
        if score >= top_score - 3
    }

    if len(values) > 1:

        return (
            None,
            "Conflicting income limits found.",
            0.0
        )

    return (
        candidates[0][1],
        evidence(candidates[0][2]),
        0.99
    )


# ============================================================
# ACADEMIC PERCENTAGE
# ============================================================

def extract_percentage(units):

    candidates = []

    patterns = [

        r"(?:minimum|at least|not less than)"
        r"\D{0,40}"
        r"(\d{1,3}(?:\.\d+)?)\s*%",

        r"(\d{1,3}(?:\.\d+)?)\s*%"
        r"\s*(?:or more|and above)"
    ]

    for text, section, score in field_units(
        units,
        "percentage"
    ):

        l = lower(text)

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        if is_document_context(text):
            continue

        if re.search(
            r"disabilit|reservation|reserved|"
            r"attendance|age|seat|quota",
            l
        ):
            continue

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if not match:
                continue

            value = float(
                match.group(1)
            )

            if not 1 <= value <= 100:
                continue

            points = score + 30

            if re.search(
                r"marks|qualifying|examination|"
                r"academic|passed|merit",
                l
            ):
                points += 10

            candidates.append(
                (
                    points,
                    value,
                    text
                )
            )

    if not candidates:
        return None, "", 0.0

    candidates.sort(
        reverse=True
    )

    best = candidates[0]

    values = {
        value
        for score, value, text
        in candidates
        if score >= best[0] - 3
    }

    if len(values) > 1:

        return (
            None,
            "Conflicting academic percentage requirements found.",
            0.0
        )

    value = best[1]

    if value.is_integer():
        value = int(value)

    return (
        value,
        evidence(best[2]),
        0.97
    )


# ============================================================
# CATEGORY
# ============================================================

CATEGORY_PATTERNS = {

    "SC": [
        r"students? belonging to sc",
        r"candidates? belonging to sc",
        r"only sc students?",
        r"scheduled caste students?",
    ],

    "ST": [
        r"students? belonging to st",
        r"candidates? belonging to st",
        r"only st students?",
        r"scheduled tribe students?",
    ],

    "OBC": [
        r"students? belonging to obc",
        r"candidates? belonging to obc",
        r"obc students?",
    ],

    "EBC": [
        r"students? belonging to ebc",
        r"ebc students?",
    ],

    "DNT": [
        r"students? belonging to dnt",
        r"dnt students?",
    ]
}


def extract_category(name, units):

    h = hints(name)

    categories = []
    evidence_map = {}

    # Name-level category.
    if h["sc"]:

        categories.append("SC")

        evidence_map["SC"] = (
            "Scheme name explicitly targets SC students."
        )

    if h["st"]:

        categories.append("ST")

        evidence_map["ST"] = (
            "Scheme name explicitly targets ST students."
        )

    if h["obc"]:

        for category in (
            "OBC",
            "EBC",
            "DNT"
        ):

            categories.append(category)

            evidence_map[category] = (
                "Scheme name explicitly identifies "
                "OBC/EBC/DNT target group."
            )

    for text, section, score in field_units(
        units,
        "category"
    ):

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        if is_document_context(text):
            continue

        l = lower(text)

        for category, patterns in CATEGORY_PATTERNS.items():

            if any(
                re.search(pattern, l)
                for pattern in patterns
            ):

                if category not in categories:

                    categories.append(
                        category
                    )

                    evidence_map[
                        category
                    ] = evidence(text)

    return (
        unique(categories),
        evidence_map,
        0.97 if categories else 0.0
    )


# ============================================================
# GENDER
# ============================================================

def extract_gender(name, units):

    if hints(name)["girl"]:

        return (
            "Female",
            "Scheme name explicitly targets girl/female students.",
            0.99
        )

    candidates = []

    for text, section, score in field_units(
        units,
        "gender"
    ):

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        if is_document_context(text):
            continue

        l = lower(text)

        if re.search(
            r"\bonly\s+(female|girl|women)\s+students?",
            l
        ):

            candidates.append(
                (
                    score + 40,
                    "Female",
                    text
                )
            )

        elif re.search(
            r"\b(female|girl|women)\s+students?",
            l
        ):

            candidates.append(
                (
                    score + 25,
                    "Female",
                    text
                )
            )

        elif re.search(
            r"\bonly\s+(male|boy)\s+students?",
            l
        ):

            candidates.append(
                (
                    score + 40,
                    "Male",
                    text
                )
            )

    if not candidates:

        return (
            "All",
            "",
            0.99
        )

    candidates.sort(
        reverse=True
    )

    return (
        candidates[0][1],
        evidence(candidates[0][2]),
        0.97
    )


# ============================================================
# DISABILITY
# ============================================================

DISABILITY_PATTERNS = [
    r"students? with .*disabilit",
    r"persons? with .*disabilit",
    r"candidates? with .*disabilit",
    r"specially abled students?",
]


def extract_disability(name, units):

    required = (
        True
        if hints(name)["disability"]
        else None
    )

    main_evidence = (
        "Scheme name explicitly targets "
        "students/persons with disabilities."
        if required
        else ""
    )

    confidence = (
        0.99
        if required
        else 0.0
    )

    thresholds = []

    for text, section, score in field_units(
        units,
        "disability"
    ):

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        # IMPORTANT:
        # "Submit Disability Certificate"
        # is NOT proof of disability eligibility.
        if is_document_context(text):
            continue

        l = lower(text)

        if any(
            re.search(pattern, l)
            for pattern in DISABILITY_PATTERNS
        ):

            required = True

            main_evidence = evidence(
                text
            )

            confidence = max(
                confidence,
                0.97
            )

        match = re.search(
            r"(?:minimum|at least|not less than|"
            r"with|having)"
            r"\D{0,25}"
            r"(\d{1,3})\s*%"
            r"\s*(?:or more\s*)?"
            r"(?:benchmark\s*)?"
            r"disabil",
            text,
            re.I
        )

        if match:

            value = int(
                match.group(1)
            )

            if 1 <= value <= 100:

                thresholds.append(
                    (
                        score + 40,
                        value,
                        text
                    )
                )

    minimum = None
    threshold_evidence = ""

    if required is True and thresholds:

        thresholds.sort(
            reverse=True
        )

        best_score = thresholds[0][0]

        values = {
            value
            for score, value, text
            in thresholds
            if score >= best_score - 3
        }

        if len(values) == 1:

            minimum = thresholds[0][1]

            threshold_evidence = evidence(
                thresholds[0][2]
            )

    return (
        required,
        minimum,
        main_evidence,
        threshold_evidence,
        confidence
    )


# ============================================================
# COURSE
# ============================================================

def extract_course(name, units):

    h = hints(name)

    courses = []
    evidence_map = {}
    confidence_map = {}

    # NAME HAS HIGHEST PRIORITY.
    if h["diploma"]:

        courses.append("Diploma")

        evidence_map["Diploma"] = (
            "Technical Diploma is explicitly "
            "specified in scheme name."
        )

        confidence_map["Diploma"] = 0.99

    elif h["degree"]:

        courses.append("Degree")

        evidence_map["Degree"] = (
            "Technical Degree is explicitly "
            "specified in scheme name."
        )

        confidence_map["Degree"] = 0.99

    elif h["pre_matric"]:

        courses.append("Pre-Matric")

        evidence_map["Pre-Matric"] = (
            "Pre-Matric is explicitly specified "
            "in scheme name."
        )

        confidence_map["Pre-Matric"] = 0.99

    elif h["post_matric"]:

        courses.append("Post-Matric")

        evidence_map["Post-Matric"] = (
            "Post-Matric is explicitly specified "
            "in scheme name."
        )

        confidence_map["Post-Matric"] = 0.99

    elif h["nmmss"]:

        courses.append("School")

        evidence_map["School"] = (
            "NMMSS is a school-level scheme."
        )

        confidence_map["School"] = 0.99

    # Direct positive course conditions only.
    patterns = {

        "Diploma":
            r"\bdiploma\b",

        "UG":
            r"\bunder\s*graduate\b|\bUG\b",

        "PG":
            r"\bpost\s*graduate\b|\bPG\b",

        "PhD":
            r"\bph\.?\s*d\.?\b|\bdoctoral\b",

        "B.Tech":
            r"\bB\.?\s*Tech\.?\b",

        "B.E.":
            r"\bB\.?\s*E\.?\b",

        "Medical":
            r"\bMBBS\b|\bBDS\b|\bmedical stream\b",

        "Professional":
            r"\bprofessional course\b|\bprofessional degree\b"
    }

    for text, section, score in field_units(
        units,
        "course"
    ):

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        if is_document_context(text):
            continue

        if is_example(text):
            continue

        l = lower(text)

        # Lateral-entry prerequisite / exclusion is not eligible course.
        if re.search(
            r"pass diploma|diploma in .* for lateral|"
            r"candidates pursuing diploma.*not",
            l
        ):
            continue

        for course, pattern in patterns.items():

            if not re.search(
                pattern,
                text,
                re.I
            ):
                continue

            # Strong positive eligibility language.
            positive = re.search(
                r"\b("
                r"eligible|eligibility|"
                r"admission|admitted|"
                r"enrolled|pursuing|"
                r"studying|"
                r"course of study|"
                r"students of"
                r")\b",
                l
            )

            if not positive:
                continue

            points = score + 25

            if course in courses:
                continue

            # Never expand a Technical Diploma scheme into Degree/PG etc.
            if h["diploma"]:
                if course != "Diploma":
                    continue

            if h["degree"]:
                if course not in (
                    "B.Tech",
                    "B.E.",
                    "UG",
                    "Medical",
                    "Professional"
                ):
                    continue

            if h["pre_matric"] or h["post_matric"] or h["nmmss"]:
                continue

            courses.append(course)

            evidence_map[
                course
            ] = evidence(text)

            confidence_map[
                course
            ] = min(
                0.95,
                0.70 + points / 100
            )

    return (
        unique(courses),
        evidence_map,
        confidence_map
    )


# ============================================================
# DOMICILE
# ============================================================

def extract_domicile(name, units):

    h = hints(name)

    if h["jkl"]:

        return (
            "Jammu & Kashmir / Ladakh",
            "Scheme name explicitly targets J&K and Ladakh.",
            0.99
        )

    if h["ner"]:

        return (
            "North Eastern Region",
            "Scheme name explicitly targets the North Eastern Region.",
            0.99
        )

    candidates = []

    patterns = {

        "Jammu & Kashmir / Ladakh":
            r"domicile.{0,100}"
            r"(jammu|kashmir|ladakh)",

        "North Eastern Region":
            r"domicile.{0,100}"
            r"north eastern",

        "Maharashtra":
            r"domicile.{0,80}"
            r"maharashtra"
    }

    for text, section, score in field_units(
        units,
        "domicile"
    ):

        if is_negative(text):
            continue

        if is_document_context(text):
            continue

        for label, pattern in patterns.items():

            if re.search(
                pattern,
                lower(text)
            ):

                candidates.append(
                    (
                        score + 30,
                        label,
                        text
                    )
                )

    if not candidates:

        return (
            "All India",
            "No restrictive domicile condition was extracted; treated as All India for matching.",
            0.60
        )

    candidates.sort(
        reverse=True
    )

    return (
        candidates[0][1],
        evidence(candidates[0][2]),
        0.97
    )


# ============================================================
# BENEFIT
# ============================================================

def extract_benefit(units):

    candidates = []

    strong_patterns = [

        r"amount of scholarship",
        r"rate of scholarship",
        r"scholarship amount",
        r"quantum of scholarship",
        r"scholarship.*per annum",
        r"scholarship.*per month",
        r"stipend.*per month",
        r"stipend.*per annum"
    ]

    for text, section, score in field_units(
        units,
        "benefit"
    ):

        if is_negative(text):
            continue

        amounts = money_mentions(text)

        if not amounts:
            continue

        l = lower(text)

        has_benefit_word = bool(
            re.search(
                r"scholarship|stipend|financial assistance",
                l
            )
        )

        has_strong_word = any(
            re.search(pattern, l)
            for pattern in strong_patterns
        )

        # Fee / hostel / computer / books are usually COMPONENTS,
        # not the scholarship amount itself.
        component_only = (
            bool(
                re.search(
                    r"tuition|fee|hostel|mess|"
                    r"computer|laptop|books?|"
                    r"stationery|equipment",
                    l
                )
            )
            and not has_strong_word
        )

        if (
            not has_benefit_word
            and section != "benefit"
        ):
            continue

        for value, raw in amounts:

            points = score

            if has_strong_word:
                points += 40

            elif has_benefit_word:
                points += 25

            if re.search(
                r"per annum|per year|annual|"
                r"per month|monthly",
                l
            ):
                points += 10

            if component_only:
                points -= 30

            candidates.append(
                {
                    "amount": value,
                    "score": points,
                    "evidence": evidence(text)
                }
            )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    details = []

    seen = set()

    for item in candidates:

        key = (
            item["amount"],
            item["evidence"]
        )

        if key in seen:
            continue

        seen.add(key)

        details.append(
            {
                "amount": item["amount"],
                "evidence": item["evidence"],
                "confidence": round(
                    min(
                        0.98,
                        0.60 +
                        max(
                            0,
                            item["score"] - 50
                        ) * 0.01
                    ),
                    2
                )
            }
        )

    if not candidates:

        return (
            None,
            [],
            "",
            0.0
        )

    top = candidates[0]

    equally_good = {
        item["amount"]
        for item in candidates
        if item["score"] >= top["score"] - 3
    }

    # Multiple equally strong amounts = DO NOT GUESS.
    if len(equally_good) > 1:

        return (
            None,
            details[:20],
            "Multiple plausible benefit amounts found; scalar benefit left null.",
            0.0
        )

    return (
        top["amount"],
        details[:20],
        top["evidence"],
        min(0.98, 0.60 + top["score"] / 100)
    )


# ============================================================
# DOCUMENTS
# ============================================================

DOCUMENT_PATTERNS = {

    "Income Certificate":
        r"income\s+certificate",

    "Caste Certificate":
        r"(?:caste|community)\s+certificate",

    "Disability Certificate":
        r"disability\s+certificate",

    "Domicile Certificate":
        r"domicile\s+certificate",

    "Bonafide Certificate":
        r"bonafide\s+certificate",

    "Death Certificate":
        r"death\s+certificate",

    "Aadhaar":
        r"\baadhaar\b",

    "Bank Account":
        r"bank\s+(?:account|details|passbook)",

    "Marksheet":
        r"mark\s*sheet|marksheet|mark-sheet",

    "Admission Proof":
        r"admission\s+(?:proof|letter|receipt|certificate)",

    "Fee Receipt":
        r"fee\s+receipt",

    "Identity Proof":
        r"identity\s+proof|id\s+proof"
}


def extract_documents(units):

    result = []
    evidence_map = {}

    for text, section, score in field_units(
        units,
        "documents"
    ):

        l = lower(text)

        if (
            section != "documents"
            and not re.search(
                r"submit|upload|enclose|attach|"
                r"document|certificate",
                l
            )
        ):
            continue

        for name, pattern in DOCUMENT_PATTERNS.items():

            if re.search(
                pattern,
                text,
                re.I
            ):

                if name not in result:

                    result.append(name)

                    evidence_map[
                        name
                    ] = evidence(text)

    return (
        result,
        evidence_map,
        0.95 if result else 0.0
    )


# ============================================================
# CONFLICT
# ============================================================

CONFLICT_PATTERNS = {

    "other scholarship": [

        r"not .*recipient.*other scholarship",
        r"not .*availing.*other scholarship",
        r"not .*receiving.*other scholarship",
        r"cannot .*other scholarship",
        r"no other scholarship"
    ],

    "other financial assistance": [

        r"not .*availing.*financial assistance",
        r"not .*receiving.*financial assistance",
        r"cannot .*financial assistance"
    ],

    "fee reimbursement": [

        r"not .*fee reimbursement",
        r"cannot .*fee reimbursement",
        r"not .*fee waiver"
    ]
}


def extract_conflicts(units):

    cannot = []
    raw = []

    for text, section, score in field_units(
        units,
        "conflict"
    ):

        l = lower(text)

        if not re.search(
            r"\bnot\b|\bcannot\b|\bshall not\b|\bineligible\b",
            l
        ):
            continue

        for label, patterns in CONFLICT_PATTERNS.items():

            if any(
                re.search(pattern, l)
                for pattern in patterns
            ):

                if label not in cannot:
                    cannot.append(label)

                raw.append(
                    evidence(text)
                )

    return (
        unique(cannot),
        unique(raw),
        0.92 if cannot else 0.0
    )


# ============================================================
# TARGET GROUPS
# ============================================================

TARGET_PATTERNS = {

    "girl_student":
        [
            r"girl students?",
            r"female students?"
        ],

    "students_with_disabilities":
        [
            r"students? with .*disabilit",
            r"specially abled"
        ],

    "orphan":
        [
            r"\borphan\b"
        ],

    "parent_died_due_to_covid":
        [
            r"parent.*(?:died|deceased).*covid",
            r"covid.*parent"
        ],

    "ward_of_armed_forces":
        [
            r"ward.*armed forces"
        ],

    "ward_of_capf_assam_rifles":
        [
            r"ward.*central armed police",
            r"assam rifles"
        ],

    "ward_of_police_personnel_martyred":
        [
            r"ward.*police personnel.*martyred",
            r"police personnel.*martyred"
        ],

    "railway_employee_ward":
        [
            r"ward.*railway",
            r"railway employee"
        ],

    "beedi_worker_ward":
        [
            r"ward.*beedi",
            r"beedi worker"
        ]
}


def extract_targets(name, units):

    h = hints(name)

    targets = []
    evidence_map = {}

    if h["girl"]:

        targets.append(
            "girl_student"
        )

        evidence_map[
            "girl_student"
        ] = (
            "Scheme name explicitly targets girl/female students."
        )

    if h["disability"]:

        targets.append(
            "students_with_disabilities"
        )

        evidence_map[
            "students_with_disabilities"
        ] = (
            "Scheme name explicitly targets students with disabilities."
        )

    for text, section, score in field_units(
        units,
        "category"
    ):

        if is_negative(text):
            continue

        if is_reservation(text):
            continue

        if is_document_context(text):
            continue

        for target, patterns in TARGET_PATTERNS.items():

            if any(
                re.search(
                    pattern,
                    lower(text)
                )
                for pattern in patterns
            ):

                if target not in targets:

                    targets.append(target)

                    evidence_map[
                        target
                    ] = evidence(text)

    return (
        unique(targets),
        evidence_map
    )


# ============================================================
# RAW CONDITIONS
# ============================================================

def extract_conditions(units):

    eligibility = []
    exclusions = []

    for unit in units:

        text = evidence(
            unit.text
        )

        if len(text) < 15:
            continue

        if (
            unit.section == "exclusion"
            or is_negative(text)
        ):

            exclusions.append(text)

        elif (
            unit.section == "eligibility"
            or eligibility_sentence(text)
        ):

            eligibility.append(text)

    return (
        unique(eligibility)[:60],
        unique(exclusions)[:60]
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classification(name):

    l = lower(name)

    if "merit based" in l:
        return "merit_based"

    if "welfare based" in l:
        return "welfare_based"

    return "other"


def provider(entry, name):

    if entry.get("provider"):
        return entry["provider"]

    l = lower(name)

    if "aicte" in l:
        return "AICTE"

    if "icar" in l:
        return "ICAR"

    if (
        "prime minister" in l
        or "pm-usp" in l
        or "pm usp" in l
        or "pm yasasvi" in l
    ):
        return "Government of India"

    return None


# ============================================================
# VALIDATION
# ============================================================

def validate(record):

    warnings = []

    e = record["eligibility"]

    # Income sanity.
    if (
        e["income_limit"] is not None
        and e["income_limit"] < 10_000
    ):

        warnings.append(
            "Income value suspiciously small."
        )

    # Academic percentage.
    if (
        e["min_academic_percentage"] is not None
        and not (
            1 <=
            e["min_academic_percentage"]
            <= 100
        )
    ):

        warnings.append(
            "Academic percentage outside valid range."
        )

    # Benefit sanity.
    if (
        record["benefit_amount"] is not None
        and record["benefit_amount"] < 100
    ):

        warnings.append(
            "Benefit amount suspiciously small."
        )

    # Disability.
    if (
        e["minimum_disability_percentage"]
        is not None
        and e["disability_required"] is not True
    ):

        warnings.append(
            "Disability percentage found without confirmed disability eligibility."
        )

    # Course contradiction.
    if (
        "Diploma" in e["course"]
        and "Degree" in e["course"]
    ):

        warnings.append(
            "Both Diploma and Degree detected; verify explicit source condition."
        )

    # Empty source.
    if not record["raw_text_file"]:

        warnings.append(
            "No extracted PDF text available."
        )

    return unique(warnings)


# ============================================================
# PARSE ONE
# ============================================================

def parse_one(entry, index):

    sid = str(
        entry.get(
            "id",
            f"SCH{index:03d}"
        )
    )

    name = clean(
        str(
            entry.get(
                "name",
                ""
            )
        )
    )

    url = (
        entry.get("source", {}).get("url")
        or entry.get("url")
        or ""
    )

    text, text_path = load_text(
        entry,
        index
    )

    # Remove extractor metadata.
    text = re.sub(
        r"^\[(?:SOURCE_URL|FINAL_URL|PDF_SHA256|EXTRACTED_AT)\].*$",
        "",
        text,
        flags=re.I | re.M
    )

    text = clean(text)

    units = make_units(text)

    income, income_ev, income_conf = extract_income(
        units
    )

    percentage, percentage_ev, percentage_conf = extract_percentage(
        units
    )

    categories, category_ev, category_conf = extract_category(
        name,
        units
    )

    gender, gender_ev, gender_conf = extract_gender(
        name,
        units
    )

    disability, disability_pct, disability_ev, disability_pct_ev, disability_conf = extract_disability(
        name,
        units
    )

    courses, course_ev, course_conf = extract_course(
        name,
        units
    )

    domicile, domicile_ev, domicile_conf = extract_domicile(
        name,
        units
    )

    benefit, benefit_details, benefit_ev, benefit_conf = extract_benefit(
        units
    )

    documents, document_ev, document_conf = extract_documents(
        units
    )

    cannot_combine, conflict_raw, conflict_conf = extract_conflicts(
        units
    )

    targets, target_ev = extract_targets(
        name,
        units
    )

    eligibility_conditions, exclusion_conditions = extract_conditions(
        units
    )

    record = {

        "id": sid,

        "name": name,

        "provider": provider(
            entry,
            name
        ),

        "source": {

            "portal": "NSP",

            "url": url,

            "last_verified": TODAY
        },

        "academic_year":
            entry.get(
                "academic_year",
                "2026-27"
            ),

        "classification": {

            "type":
                classification(name)
        },

        "eligibility": {

            "income_limit":
                income,

            "category":
                categories,

            "course":
                courses,

            "min_academic_percentage":
                percentage,

            "gender":
                gender,

            "state_domicile":
                domicile,

            "disability_required":
                disability,

            "minimum_disability_percentage":
                disability_pct
        },

        "target_groups":
            targets,

        "eligibility_conditions":
            eligibility_conditions,

        "exclusion_conditions":
            exclusion_conditions,

        "benefit_amount":
            benefit,

        "benefit_details":
            benefit_details,

        "required_documents":
            documents,

        "deadline":
            None,

        "conflict_rules": {

            "cannot_combine_with":
                cannot_combine,

            "can_combine_with":
                [],

            "raw_rules":
                conflict_raw
        },

        "evidence": {

            "income":
                income_ev,

            "percentage":
                percentage_ev,

            "category":
                category_ev,

            "course":
                course_ev,

            "gender":
                gender_ev,

            "disability":
                disability_ev,

            "disability_percentage":
                disability_pct_ev,

            "domicile":
                domicile_ev,

            "benefit":
                benefit_ev,

            "documents":
                document_ev,

            "conflicts":
                conflict_raw,

            "eligibility_conditions":
                eligibility_conditions,

            "exclusion_conditions":
                exclusion_conditions
        },

        "data_quality": {

            "parser_version":
                PARSER_VERSION,

            "text_length":
                len(text),

            "manual_review_required":
                True,

            "warnings":
                [],

            "field_confidence": {

                "income_limit":
                    round(income_conf, 2),

                "min_academic_percentage":
                    round(percentage_conf, 2),

                "category":
                    round(category_conf, 2),

                "course":
                    round(
                        max(
                            course_conf.values(),
                            default=0
                        ),
                        2
                    ),

                "gender":
                    round(gender_conf, 2),

                "disability_required":
                    round(disability_conf, 2),

                "minimum_disability_percentage":
                    (
                        round(disability_conf, 2)
                        if disability_pct is not None
                        else 0
                    ),

                "state_domicile":
                    round(domicile_conf, 2),

                "benefit_amount":
                    round(benefit_conf, 2),

                "required_documents":
                    round(document_conf, 2),

                "conflict_rules":
                    round(conflict_conf, 2)
            }
        },

        "raw_text_file":
            (
                str(
                    text_path.relative_to(DATA)
                ).replace("\\", "/")
                if text_path
                else None
            )
    }

    warnings = validate(
        record
    )

    confidence = record[
        "data_quality"
    ][
        "field_confidence"
    ]

    weak = []

    for field, conf in confidence.items():

        if conf < 0.85:

            value = None

            if field in record["eligibility"]:
                value = record[
                    "eligibility"
                ][field]

            elif field == "benefit_amount":
                value = record[
                    "benefit_amount"
                ]

            elif field == "required_documents":
                value = record[
                    "required_documents"
                ]

            elif field == "conflict_rules":
                value = record[
                    "conflict_rules"
                ][
                    "cannot_combine_with"
                ]

            if value not in (
                None,
                [],
                ""
            ):

                weak.append(
                    field
                )

    if weak:

        warnings.append(
            "Weak evidence: "
            + ", ".join(weak)
        )

    # Benefit ambiguity should force review.
    if (
        record["benefit_amount"] is None
        and record["benefit_details"]
    ):

        warnings.append(
            "Benefit has multiple plausible amounts."
        )

    record[
        "data_quality"
    ][
        "warnings"
    ] = unique(warnings)

    record[
        "data_quality"
    ][
        "manual_review_required"
    ] = bool(
        warnings
        or not text
    )

    return record


# ============================================================
# MAIN
# ============================================================

def main():

    scholarships = get_scholarships()

    output = {

        "metadata": {

            "academic_year":
                "2026-27",

            "source":
                "NSP",

            "description":
                "Evidence-first scholarship extraction from official NSP documents.",

            "parser_version":
                PARSER_VERSION,

            "generated_on":
                TODAY,

            "rule":
                "Never convert ambiguous source text into a guessed eligibility value."
        },

        "scholarships":
            []
    }

    for index, entry in enumerate(
        scholarships,
        start=1
    ):

        record = parse_one(
            entry,
            index
        )

        output[
            "scholarships"
        ].append(
            record
        )

        e = record[
            "eligibility"
        ]

        print(
            f"{index:02d} "
            f"{record['id']} | "
            f"income={e['income_limit']} | "
            f"pct={e['min_academic_percentage']} | "
            f"category={e['category']} | "
            f"course={e['course']} | "
            f"gender={e['gender']} | "
            f"disability={e['disability_required']} "
            f"{e['minimum_disability_percentage']}% | "
            f"domicile={e['state_domicile']} | "
            f"benefit={record['benefit_amount']} | "
            f"review={record['data_quality']['manual_review_required']}"
        )

    save_json(
        OUTPUT_FILE,
        output
    )

    print()
    print(
        "=============================================="
    )
    print(
        "FINAL PARSING COMPLETE"
    )
    print(
        "=============================================="
    )
    print(
        f"Total: {len(output['scholarships'])}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
