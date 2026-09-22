import json
from copy import deepcopy
from pathlib import Path

SRC = Path("data/scholarships_detailed_v3.json")
OUT = Path("data/scholarships_clean_v1.json")

OVERRIDES = {
  "SCH003": {
    "category": [],
    "course": [
      "Degree"
    ],
    "gender": "All",
    "disability_required": false,
    "minimum_disability_percentage": null,
    "conflict_rules": {
      "cannot_combine_with": [
        "central government scholarship",
        "state government scholarship",
        "AICTE-sponsored scholarship"
      ],
      "can_combine_with": []
    }
  },
  "SCH004": {
    "category": [],
    "course": [
      "Degree",
      "Engineering",
      "Medical"
    ],
    "state_domicile": [
      "Jammu & Kashmir",
      "Ladakh"
    ],
    "disability_required": null,
    "minimum_disability_percentage": null
  },
  "SCH005": {
    "category": [],
    "course": [
      "Degree"
    ],
    "gender": "Female",
    "disability_required": false,
    "minimum_disability_percentage": null
  },
  "SCH006": {
    "category": [],
    "course": [
      "Diploma"
    ],
    "gender": "Female",
    "disability_required": false,
    "minimum_disability_percentage": null
  },
  "SCH007": {
    "category": [],
    "course": [
      "Diploma"
    ],
    "disability_required": true,
    "minimum_disability_percentage": 40
  },
  "SCH008": {
    "category": [],
    "course": [
      "Degree"
    ],
    "disability_required": true,
    "minimum_disability_percentage": 40
  },
  "SCH009": {
    "category": [],
    "course": [
      "Diploma"
    ],
    "conflict_rules": {
      "cannot_combine_with": [
        "central government scholarship",
        "state government scholarship",
        "AICTE-sponsored scholarship"
      ],
      "can_combine_with": []
    }
  },
  "SCH010": {
    "category": [],
    "course": [
      "PG"
    ]
  },
  "SCH011": {
    "category": [],
    "course": [
      "UG"
    ]
  },
  "SCH012": {
    "eligibility_reset": true
  },
  "SCH013": {
    "eligibility_reset": true
  },
  "SCH014": {
    "category": [
      "OBC",
      "EBC",
      "DNT"
    ],
    "course": [
      "School"
    ]
  },
  "SCH015": {
    "course": [
      "Full-time prescribed course"
    ]
  },
  "SCH016": {
    "eligibility_reset": true
  },
  "SCH017": {
    "course": [
      "UG",
      "PG"
    ],
    "min_academic_percentage": null
  },
  "SCH018": {
    "course": [
      "UG"
    ]
  },
  "SCH019": {
    "category": [
      "General",
      "OBC",
      "Underprivileged States",
      "SC",
      "ST",
      "Physically Challenged"
    ],
    "course": [
      "PG"
    ],
    "min_academic_percentage": 60
  },
  "SCH020": {
    "course": [
      "PG"
    ]
  },
  "SCH021": {
    "category": [
      "General",
      "OBC",
      "Underprivileged States",
      "SC",
      "ST",
      "Physically Challenged"
    ],
    "course": [
      "PG",
      "PhD"
    ],
    "min_academic_percentage": 60
  },
  "SCH022": {
    "category": [
      "SC"
    ],
    "course": [
      "Full-time prescribed course"
    ],
    "min_academic_percentage": null
  },
  "SCH023": {
    "category": [
      "SC",
      "OBC",
      "PM CARES Children beneficiaries"
    ],
    "course": [
      "Competitive-exam coaching"
    ],
    "min_academic_percentage": null
  },
  "SCH024": {
    "category": [],
    "course": [
      "Pre-matric"
    ],
    "min_academic_percentage": null
  },
  "SCH025": {
    "category": [],
    "course": [
      "Post-matric"
    ],
    "min_academic_percentage": null
  },
  "SCH026": {
    "category": [],
    "course": [
      "Top-class education"
    ],
    "min_academic_percentage": null
  },
  "SCH027": {
    "category": [],
    "course": [
      "School"
    ],
    "min_academic_percentage": null
  },
  "SCH028": {
    "category": [],
    "course": [
      "UG",
      "PG",
      "Professional degree"
    ],
    "min_academic_percentage": null,
    "disability_required": null,
    "minimum_disability_percentage": null,
    "conflict_rules": {
      "cannot_combine_with": [
        "other merit scholarship",
        "state scholarship",
        "fee waiver",
        "reimbursement scheme"
      ],
      "can_combine_with": []
    }
  },
  "SCH029": {
    "category": [
      "ST"
    ],
    "course": [
      "Higher education"
    ]
  },
  "SCH030": {
    "category": [],
    "course": [
      "Higher professional course"
    ],
    "conflict_rules": {
      "cannot_combine_with": [
        "other scholarship"
      ],
      "can_combine_with": []
    }
  },
  "SCH031": {
    "category": [],
    "course": [
      "Professional degree"
    ],
    "min_academic_percentage": 60
  }
}

data = json.loads(SRC.read_text(encoding="utf-8"))
clean = deepcopy(data)

for s in clean["scholarships"]:
    sid = s["id"]
    ov = OVERRIDES.get(sid, {})
    e = s.setdefault("eligibility", {})
    if ov.get("eligibility_reset"):
        e.update({"income_limit": None, "category": [], "course": [],
                  "min_academic_percentage": None, "gender": "All",
                  "state_domicile": "All India", "disability_required": None,
                  "minimum_disability_percentage": None})
        s["benefit_amount"] = None
        s["required_documents"] = []
    else:
        for key, value in ov.items():
            if key in e:
                e[key] = value
            elif key == "conflict_rules":
                s["conflict_rules"] = value

    s["data_quality"] = {
        "source_type": "official NSP scheme document",
        "extraction_source": s.get("raw_text_file"),
        "normalized": sid in OVERRIDES,
        "manual_review_required": True
    }

clean["metadata"]["version"] = "clean_v1"
clean["metadata"]["description"] = (
    "Conservatively normalized scholarship data from v3 extraction. "
    "Uncertain fields remain null/empty."
)
OUT.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Created: {OUT}")
