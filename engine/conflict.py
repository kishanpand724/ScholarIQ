from eligibility import find_eligible_scholarships
from combination import generate_combinations


def check_conflict(combo):

    scholarships = combo["scholarships"]

    for i in range(len(scholarships)):

        for j in range(i + 1, len(scholarships)):

            scholarship_a = scholarships[i]
            scholarship_b = scholarships[j]

            a_conflicts = scholarship_a[
                "conflict_rules"
            ].get(
                "cannot_combine_with",
                []
            )

            b_conflicts = scholarship_b[
                "conflict_rules"
            ].get(
                "cannot_combine_with",
                []
            )

            # Check both directions
            if (
                scholarship_b["id"] in a_conflicts
                or
                scholarship_a["id"] in b_conflicts
            ):

                return True, (
                    f"{scholarship_a['id']} cannot be combined "
                    f"with {scholarship_b['id']}"
                )

    return False, "No conflict"


def filter_valid_combinations(
    all_combinations,
    scholarship_data
):

    scholarship_map = {
        scholarship["id"]: scholarship
        for scholarship in scholarship_data
    }

    valid_combinations = []
    conflicting_combinations = []

    for combo in all_combinations:

        full_combo = {
            "scholarships": [
                scholarship_map[item["id"]]
                for item in combo["scholarships"]
            ],

            "total_benefit": combo["total_benefit"]
        }

        has_conflict, reason = check_conflict(
            full_combo
        )

        if has_conflict:

            conflicting_combinations.append({

                "scholarships": combo["scholarships"],

                "total_benefit": combo["total_benefit"],

                "reason": reason
            })

        else:

            valid_combinations.append(combo)

    return (
        valid_combinations,
        conflicting_combinations
    )


def get_valid_combinations(
    student,
    scholarships
):

    # Step 1: Find eligible scholarships
    eligible, rejected = find_eligible_scholarships(
        student,
        scholarships
    )

    # Step 2: Generate all combinations
    all_combinations = generate_combinations(
        eligible
    )

    # Step 3: Remove conflicting combinations
    (
        valid_combinations,
        conflicting_combinations
    ) = filter_valid_combinations(
        all_combinations,
        scholarships
    )

    return (
        eligible,
        all_combinations,
        valid_combinations,
        conflicting_combinations
    )