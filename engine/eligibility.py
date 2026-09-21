import json
import os


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize(value):
    return str(value).strip().lower().replace(".", "")


def check_eligibility(student, scholarship):
    rules = scholarship["eligibility"]

    # Income
    if student["income"] > rules["income_limit"]:
        return False, "Income exceeds the scholarship limit"

    # Category
    if normalize(student["category"]) not in [
        normalize(category)
        for category in rules["category"]
    ]:
        return False, "Category not eligible"

    # Course
    if normalize(student["course"]) not in [
        normalize(course)
        for course in rules["course"]
    ]:
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
    required_domicile = rules.get("state_domicile", "All India")

    if normalize(required_domicile) != "all india":
        if normalize(student["domicile"]) != normalize(required_domicile):
            return False, "Domicile requirement not satisfied"

    # Disability
    disability_required = rules.get("disability_required", False)

    if disability_required:

        if not student.get("has_disability", False):
            return False, "Disability requirement not satisfied"

        minimum_disability = rules.get(
            "minimum_disability_percentage", 0
        )

        student_disability = student.get(
            "disability_percentage", 0
        )

        if student_disability < minimum_disability:
            return False, "Disability percentage is below the required minimum"

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
