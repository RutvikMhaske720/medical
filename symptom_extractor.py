import json

from google.genai import types
from soap_generator import client, MODEL_NAME


# ==========================================
# 1. SYMPTOM OUTPUT STRUCTURE
# ==========================================

SYMPTOM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symptoms": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "symptom": {
                        "type": "STRING"
                    },
                    "status": {
                        "type": "STRING",
                        "enum": ["present", "denied", "unclear"]
                    },
                    "duration": {
                        "type": "STRING"
                    },
                    "severity": {
                        "type": "STRING"
                    },
                    "evidence": {
                        "type": "STRING"
                    }
                },
                "required": [
                    "symptom",
                    "status",
                    "duration",
                    "severity",
                    "evidence"
                ]
            }
        }
    },
    "required": ["symptoms"]
}


# ==========================================
# 2. EXTRACT SYMPTOMS
# ==========================================

def extract_symptoms(transcript):

    prompt = f"""
    You are MedhaJiva, an AI clinical documentation assistant.

    Extract symptoms explicitly mentioned in the
    following doctor-patient conversation.

    RULES:

    1. Extract only symptoms mentioned in the transcript.
    2. Do not invent or assume symptoms.
    3. Mark a symptom as "present" when it is reported
       as experienced by the patient.
    4. Mark it as "denied" when the patient explicitly
       says they do not have that symptom.
    5. Mark it as "unclear" when its presence cannot
       be determined from the conversation.
    6. Record duration and severity only if stated.
    7. If duration or severity is not mentioned,
       use "Not mentioned".
    8. Include a short supporting quote from the transcript.
    9. Do not extract diagnoses as symptoms.
    10. Do not treat a doctor's question as proof that
        the patient has a symptom.
    11. Do not treat silence or missing information
        as a denial.

    This is symptom documentation, not diagnosis.

    TRANSCRIPT:

    {transcript}
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SYMPTOM_SCHEMA,
            temperature=0.1
        )
    )

    return json.loads(response.text)
