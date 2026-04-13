import json

with open("data/structure.json", "r") as f:
    data = json.load(f)

mapping = {
    # Summer
    "s-e-p": {"name": "software-development-project", "module": "INF-02-20-M-2"},
    "algodat": {"name": "algorithms-and-data-structures", "module": "INF-02-06-M-2"},
    "kss": {"name": "mathematics-for-computer-science-combinatorics-stochastics-and-statistics", "module": "MAT-02-12-M-1"},
    "mosy": {"name": "modeling-and-systems", "module": "INF-02-11-M-2"}, # Guessing INF-02-11
    "insy": {"name": "information-systems", "module": "INF-00-12-M-2"},
    "fsub": {"name": "formal-languages-and-computability", "module": "INF-02-04-M-2"},
    "abschlussarbeiten": {"name": "bachelors-thesis", "module": "INF-81-10-M-4"},
    "progpra": {"name": "programming-and-modeling", "module": "INF-02-12-M-2"},
    "kosy": {"name": "communication-systems", "module": "INF-02-13-M-2"},
    "dira": {"name": "digital-systems-and-computer-architecture", "module": "INF-02-09-M-2"},
    "logik": {"name": "logic-and-semantics-of-programming-languages", "module": "INF-02-05-M-2"},
    "ki": {"name": "artificial-intelligence", "module": "INF-02-17-M-2"},
    "scicomp": {"name": "scientific-computing", "module": "INF-02-07-M-2"},
    "v-n-p": {"name": "distributed-and-concurrent-systems", "module": "INF-02-03-M-2"},
    "infges": {"name": "computer-science-and-society", "module": "INF-02-22-M-2"},
    "netsec": {"name": "secure-systems", "module": "INF-02-15-M-2"},
    "rosy": {"name": "computer-organization-and-system-software", "module": "INF-02-10-M-2"},
    "gdp": {"name": "concepts-of-programming", "module": "INF-02-01-M-2"}, # From prompt
    "mathe": {"name": "mathematics-for-computer-science-analysis", "module": "MAT-02-13-M-1"}
}

for season in ["summer", "winter"]:
    for c in data.get(season, {}).get("courses", []):
        old_name = c["name"]
        if old_name in mapping:
            c["name"] = mapping[old_name]["name"]
            c["module"] = mapping[old_name]["module"]

with open("data/structure.json", "w") as f:
    json.dump(data, f, indent=4)
