import json
import os

from conflict import get_valid_combinations


def calculate_score(combination):

    total_benefit = combination["total_benefit"]

    scholarship_count = len(
        combination["scholarships"]
    )

    # Simple prototype scoring
    score = total_benefit + (
        scholarship_count * 1000
    )

    return score


def rank_combinations(valid_combinations):

    ranked = []

    for combination in valid_combinations:

        score = calculate_score(
            combination
        )

        ranked.append({

            "scholarships": combination[
                "scholarships"
            ],

            "total_benefit": combination[
                "total_benefit"
            ],

            "score": score
        })

    ranked.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked


def get_top_recommendations(
    valid_combinations,
    limit=3
):

    ranked = rank_combinations(
        valid_combinations
    )

    return ranked[:limit]


if __name__ == "__main__":

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

    # Load data
    with open(
        student_path,
        "r",
        encoding="utf-8"
    ) as file:
        student = json.load(file)

    with open(
        scholarships_path,
        "r",
        encoding="utf-8"
    ) as file:
        scholarships = json.load(file)

    # Run complete MUSA CodeX pipeline
    (
        eligible,
        all_combinations,
        valid_combinations,
        conflicting_combinations
    ) = get_valid_combinations(
        student,
        scholarships
    )

    # Get Top 3
    top_recommendations = get_top_recommendations(
        valid_combinations,
        limit=3
    )

    # Final output
    print("\n======================================")
    print("          MUSA CODEX")
    print("     TOP 3 RECOMMENDATIONS")
    print("======================================")

    for index, recommendation in enumerate(
        top_recommendations,
        start=1
    ):

        print(f"\n#{index}")

        print("Scholarships:")

        for scholarship in recommendation[
            "scholarships"
        ]:

            print(
                f"  - {scholarship['id']} | "
                f"{scholarship['name']}"
            )

        print(
            f"Total Benefit: ₹"
            f"{recommendation['total_benefit']}"
        )

    print("\n======================================")