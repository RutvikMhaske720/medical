from database import (
    initialize_database,
    add_patient,
    save_consultation,
    get_patient_consultations
)


# Initialize database

initialize_database()

print("Database initialized successfully!")


# Add a fictional patient

patient_id = add_patient(
    name="Demo Patient",
    age=25
)

print("\nPatient added!")
print("Patient ID:", patient_id)


# Sample transcript

transcript = """
Patient reports fever for three days,
headache and body pain.
Patient denies cough.
"""


# Sample SOAP notes

soap_notes = {
    "subjective": "Fever, headache and body pain.",
    "objective": "No measured findings documented.",
    "assessment": "No definitive assessment documented.",
    "plan": "Further examination discussed.",
    "missing_information": ["Temperature measurement"]
}


# Sample extracted symptoms

symptoms = [
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


# Save consultation

consultation_id = save_consultation(
    patient_id=patient_id,
    transcript=transcript,
    soap_notes=soap_notes,
    symptoms=symptoms,
    clinical_results=[]
)

print("\nConsultation saved!")
print("Consultation ID:", consultation_id)


# Retrieve consultation

records = get_patient_consultations(patient_id)

print("\n========== STORED CONSULTATIONS ==========")

for record in records:

    print("\nConsultation ID:", record["consultation_id"])

    print("Date:", record["consultation_date"])

    print("Transcript:", record["transcript"])

    print("SOAP Notes:", record["soap_notes"])

    print("Symptoms:", record["symptoms"])

    print("Review Status:", record["review_status"])


print("\nDatabase test completed!")
