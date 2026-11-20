from symptom_extractor import extract_symptoms


sample_transcript = """
Doctor: What problem are you experiencing?

Patient: I have had fever for three days.
I also have headache and body pain.

Doctor: Do you have a cough?

Patient: No, I don't have a cough.

Doctor: Are you experiencing vomiting?

Patient: No.
"""


print("Extracting symptoms...")

result = extract_symptoms(sample_transcript)

print("\n========== EXTRACTED SYMPTOMS ==========")

for item in result["symptoms"]:

    print("\nSymptom:", item["symptom"])
    print("Status:", item["status"])
    print("Duration:", item["duration"])
    print("Severity:", item["severity"])
    print("Evidence:", item["evidence"])
