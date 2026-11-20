from clinical_decision_support import match_conditions


# Fictional patient symptoms

extracted_symptoms = [

    {
        "symptom": "fever",
        "status": "present"
    },

    {
        "symptom": "headache",
        "status": "present"
    },

    {
        "symptom": "body pain",
        "status": "present"
    },

    {
        "symptom": "cough",
        "status": "denied"
    }

]


# Generate possible condition matches

results = match_conditions(extracted_symptoms)


# Display results

print("\n========== CLINICAL DECISION SUPPORT ==========")

if results:

    for item in results:

        print("\nCondition:", item["name"])

        print("Matching symptoms:", item["matched_symptoms"])

        print("Matching symptom count:", item["match_count"])

        print("Explicitly denied symptoms:", item["denied_symptoms"])

        print("Reference:", item["source"])

        print("Limitation:", item["limitations"])

        print("--------------------------------------")

else:

    print("No matching conditions found.")
