import json
import sys

try:
    with open("structure.json", "r") as f:
        data = json.load(f)

    # 1. Update kss
    for season in ["summer", "winter"]:
        for c in data.get(season, {}).get("courses", []):
            if c["id"] == 1229812364677873754: # kss
                c["name"] = "mathematics-for-computer-science-combinatorics-stochastics-and-statistics"
            elif c["id"] == 1429792896214896761: # 3dcv
                c["name"] = "3d-computer-vision"
            elif c["id"] == 1429789841889165352: # ewgai
                c["name"] = "engineering-with-generative-ai"
            elif c["id"] == 1267989044713881621: # comgeom
                c["name"] = "computational-geometry"
            elif c["id"] == 1293583225133994024: # hci
                c["name"] = "human-computer-interaction"
            elif c["id"] == 1293583636091899945: # datawiz
                c["name"] = "data-visualisation"
            elif c["id"] == 1348657198015709285: # netsec
                c["name"] = "network-security"
                # Keep module INF-02-15-M-2? The prompt says "netsec - secure-systems should be called network security", I'll keep the module info
            elif c["id"] == 1052258535167229952: # mathe
                c["name"] = "mathematics-for-computer-science-algebraic-structures"
                c["module"] = "MAT-02-11-M-1"

    # Add the new Analysis course (let's put it in winter)
    data["winter"]["courses"].append({
        "name": "mathematics-for-computer-science-analysis",
        "id": 999999999999999999, # Placeholder
        "role": {
            "name": "analysis",
            "id": 999999999999999998
        },
        "links": [],
        "module": "MAT-02-13-M-1"
    })

    with open("structure.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
