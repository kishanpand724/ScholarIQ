from itertools import combinations


def generate_combinations(eligible_scholarships):

    all_combinations = []

    n = len(eligible_scholarships)

    # Generate every possible non-empty combination
    for r in range(1, n + 1):

        for combo in combinations(
            eligible_scholarships,
            r
        ):

            total_benefit = sum(
                scholarship["benefit_amount"]
                for scholarship in combo
            )

            all_combinations.append({

                "scholarships": [
                    {
                        "id": scholarship["id"],
                        "name": scholarship["name"]
                    }

                    for scholarship in combo
                ],

                "total_benefit": total_benefit
            })

    return all_combinations
