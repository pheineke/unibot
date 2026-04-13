import json

try:
    with open("data/structure.json", "r") as f:
        data = json.load(f)

    # Map modules to sections based on the HTML structure
    module_to_section = {
        # Software Development -> section-0
        "INF-02-01-M-2": "section-0", # Concepts of Programming
        "INF-02-03-M-2": "section-0", # Distributed and Concurrent Systems
        "INF-02-06-M-2": "section-0", # Algorithms and Data Structures
        "INF-02-12-M-2": "section-0", # Programming and Modeling
        "INF-02-18-M-2": "section-0", # Project Management
        "INF-02-20-M-2": "section-0", # Software Development Project

        # Computer Science Systems -> section-2
        "INF-02-09-M-2": "section-2", # Digital Systems and Computer Architecture
        "INF-02-10-M-2": "section-2", # Computer Organization and System Software
        "INF-00-12-M-2": "section-2", # Information Systems
        "INF-02-13-M-2": "section-2", # Communication Systems
        "INF-02-15-M-2": "section-2", # Secure Systems (network-security)
        "INF-02-07-M-2": "section-2", # Scientific Computing
        "INF-02-17-M-2": "section-2", # Artificial Intelligence

        # Theoretical Foundations -> section-1
        "MAT-02-11-M-1": "section-1", # Maths: Algebraic Structures
        "MAT-02-12-M-1": "section-1", # Maths: Combinatorics...
        "MAT-02-13-M-1": "section-1", # Maths: Analysis
        "INF-02-04-M-2": "section-1", # Formal Languages
        "INF-02-05-M-2": "section-1", # Logic and Semantics

        # Interdisciplinary Qualification -> section-3
        "INF-02-08-M-2": "section-3", # Study Planning
        "INF-02-22-M-2": "section-3", # Computer Science and Society
        "INF-01-11-M-4": "section-3", # Bachelor Seminar
        
        # Thesis
        "INF-81-10-M-4": "thesis"
    }

    # Go through courses and assign sections
    for season in ["summer", "winter"]:
        for c in data.get(season, {}).get("courses", []):
            mod = c.get("module")
            if mod in module_to_section:
                c["section"] = module_to_section[mod]
            else:
                # If no specific compulsory match, handle special cases
                if c["name"] == "web20":
                    c["section"] = "supplement"
                elif c["name"] == "abschlussarbeiten" or "thesis" in c["name"]:
                    c["section"] = "thesis"
                else:
                    c["section"] = "specialization"
                    if "specialization_ids" not in c:
                        # Placeholder array
                        c["specialization_ids"] = []

    # Also handle 'various' if it exists
    if "various" in data and "section" not in data["various"]:
        data["various"]["section"] = "thesis"

    with open("data/structure.json", "w") as f:
        json.dump(data, f, indent=4)
        
    print("Successfully structured sections!")
    
except Exception as e:
    print(f"Error: {e}")
