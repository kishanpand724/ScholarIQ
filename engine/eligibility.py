import json
import os


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# Text ko comparison ke liye normalize karta hai
def normalize(value):
    return str(value).strip().lower().replace(".", "")


def check_eligibility(student, scholarship):
    rules = scholarship["eligibility"]

    # Income
    if student["income"] > rules["income_limit"]:
        return False, "Income exceeds the scholarship limit"

    # Category
    student_category = normalize(student["category"])
    allowed_categories = [
        normalize(category) for category in rules["category"]
    ]

    if student_category not in allowed_categories:
        return False, "Category not eligible"

    # Course
    student_course = normalize(student["course"])
    allowed_courses = [
        normalize(course) for course in rules["course"]
    ]

    if student_course not in allowed_courses:
        return False, "Course not eligible"

    # Academic percentage
    if student["percentage"] < rules["min_academic_percentage"]:
        return False, "Academic percentage is below the required minimum"

    # Gender
    required_gender = rules.get("gender", "All")

    if normalize(required_gender) != "all":
        if normalize(student["gender"]) != normalize(required_gender):
            return False, "Gender requirement not satisfied"

    # Domicile
    required_domicile = rules["state_domicile"]

    if normalize(required_domicile) != "all india":
        if normalize(student["domicile"]) != normalize(required_domicile):
            return False, "Domicile requirement not satisfied"

    return True, "All eligibility conditions satisfied"


def find_eligible_scholarships(student, scholarships):
    eligible = []
    rejected = []

    for scholarship in scholarships:

        is_eligible, reason = check_eligibility(
            student,
            scholarship
        )

        if is_eligible:
            eligible.append(scholarship)

        else:
            rejected.append({
                "id": scholarship["id"],
                "name": scholarship["name"],
                "reason": reason
            })

    return eligible, rejected


# --------------------------------------
# FILE PATHS
# --------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

student_path = os.path.join(
    BASE_DIR,
    "data",
    "student.json"
)

scholarships_path = os.path.join(
    BASE_DIR,
    "data",
    "scholarships.json"
)


# --------------------------------------
# LOAD DATA
# --------------------------------------

student = load_json(student_path)
scholarships = load_json(scholarships_path)


# --------------------------------------
# CHECK ELIGIBILITY
# --------------------------------------

eligible, rejected = find_eligible_scholarships(
    student,
    scholarships
)


# --------------------------------------
# OUTPUT
# --------------------------------------

print("\n======================================")
print("       MUSA CODEX - ELIGIBILITY")
print("======================================\n")

print("ELIGIBLE SCHOLARSHIPS:\n")

for scholarship in eligible:
    print(
        f"{scholarship['id']} | "
        f"{scholarship['name']} | "
        f"Benefit: ₹{scholarship['benefit_amount']}"
    )


print("\n--------------------------------------")
print("NOT ELIGIBLE:\n")

for scholarship in rejected:
    print(
        f"{scholarship['id']} | "
        f"{scholarship['name']}"
    )

    print(
        f"Reason: {scholarship['reason']}\n"
    )


print("--------------------------------------")
print(f"Total Eligible: {len(eligible)}")
print(f"Total Rejected: {len(rejected)}")
print("======================================")
