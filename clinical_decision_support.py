import json
from pathlib import Path


# ==========================================
# 1. LOAD KNOWLEDGE BASE
# ==========================================

def load_knowledge_base():

    file_path = Path(__file__).parent / "clinical_knowledge_base.json"

    with open(file_path, "r", encoding="utf-8") as file:

        data = json.load(file)

    return data["conditions"]


# ==========================================
# 2. NORMALIZE SYMPTOMS
# ==========================================

def normalize_symptoms(symptoms):

    aliases = {

        "body pain": "body aches",
        "muscle pain": "body aches",
        "muscle aches": "body aches",

        "stomach ache": "stomach pain",
        "abdominal pain": "stomach pain",

        "blocked nose": "nasal congestion",
        "stuffy nose": "nasal congestion",

        "nasal discharge": "runny nose",
        "rhinorrhea": "runny nose",

        "high temperature": "fever",
        "raised temperature": "fever"
    }

    normalized = set()

    for symptom in symptoms:

        name = symptom.strip().lower()

        name = aliases.get(name, name)

        normalized.add(name)

    return normalized


# ==========================================
# 3. MATCH CONDITIONS
# ==========================================

def match_conditions(extracted_symptoms):

    conditions = load_knowledge_base()

    present_symptoms = []
    denied_symptoms = []

    # Separate present and denied symptoms

    for item in extracted_symptoms:

        symptom = item["symptom"]

        status = item["status"].lower()

        if status == "present":

            present_symptoms.append(symptom)

        elif status == "denied":

            denied_symptoms.append(symptom)

    # Normalize symptom names

    present = normalize_symptoms(present_symptoms)

    denied = normalize_symptoms(denied_symptoms)

    results = []

    # Compare patient symptoms with each condition

    for condition in conditions:

        associated = normalize_symptoms(
            condition["associated_symptoms"]
        )

        matched = present.intersection(associated)

        denied_matches = denied.intersection(associated)

        # Only show conditions with at least one
        # matching present symptom

        if matched:

            results.append({

                "id": condition["id"],

                "name": condition["name"],

                "matched_symptoms": sorted(matched),

                "denied_symptoms": sorted(denied_matches),

                "match_count": len(matched),

                "source": condition["source"],

                "limitations": condition["limitations"]

            })

    # Sort by number of matching symptoms

    results.sort(
        key=lambda item: item["match_count"],
        reverse=True
    )

    return results
