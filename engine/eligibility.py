import json
import os


# ==============================
# LOAD JSON FILE
# ==============================

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ==============================
# CHECK ONE SCHOLARSHIP
# ==============================

def check_eligibility(student, scholarship):

    rules = scholarship["eligibility"]

    # Income
    if student["income"] > rules["income_limit"]:
        return False, "Income exceeds limit"

    # Category
    if student["category"] not in rules["category"]:
        return False, "Category not eligible"

    # Course
    if student["course"] not in rules["course"]:
        return False, "Course not eligible"

    # Percentage
    if student["percentage"] < rules["min_academic_percentage"]:
        return False, "Percentage too low"

    # Gender
    required_gender = rules.get("gender", "All")

    if required_gender != "All":
        if student["gender"] != required_gender:
            return False, "Gender requirement not satisfied"

    # Domicile
    required_domicile = rules.get("state_domicile", "All India")

    if required_domicile != "All India":
        if student["domicile"] != required_domicile:
            return False, "Domicile requirement not satisfied"

    return True, "Eligible"


# ==============================
# FIND ALL ELIGIBLE
# ==============================

def find_eligible_scholarships(student, scholarships):

    eligible = []
    rejected = []

    for scholarship in scholarships:

        result, reason = check_eligibility(
            student,
            scholarship
        )

        if result:
            eligible.append(scholarship)
        else:
            rejected.append({
                "id": scholarship["id"],
                "name": scholarship["name"],
                "reason": reason
            })

    return eligible, rejected


# ==============================
# PROJECT PATH
# ==============================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
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


# ==============================
# LOAD DATA
# ==============================

student = load_json(student_path)
scholarships = load_json(scholarships_path)


# ==============================
# RUN ENGINE
# ==============================

eligible, rejected = find_eligible_scholarships(
    student,
    scholarships
)


# ==============================
# OUTPUT
# ==============================

print("\n======================================")
print("       MUSA CODEX - ELIGIBILITY")
print("======================================\n")


print("ELIGIBLE SCHOLARSHIPS:\n")

for scholarship in eligible:

    print(
        scholarship["id"],
        "|",
        scholarship["name"],
        "| Benefit: ₹",
        scholarship["benefit_amount"]
    )


print("\n--------------------------------------")
print("NOT ELIGIBLE:\n")

for scholarship in rejected:

    print(
        scholarship["id"],
        "|",
        scholarship["name"]
    )

    print(
        "Reason:",
        scholarship["reason"]
    )

    print()


print("--------------------------------------")

print(
    "Total Eligible:",
    len(eligible)
)

print(
    "Total Rejected:",
    len(rejected)
)

print("======================================")

