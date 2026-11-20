import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================

from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("GEMINI_API_KEY")

print("API key loaded:", bool(API_KEY))

if not API_KEY:
    raise ValueError("Gemini API key not found!")


# ==========================================
# 2. INITIALIZE GEMINI CLIENT
# ==========================================

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        timeout=60000,
        retry_options=types.HttpRetryOptions(
            attempts=1
        )
    )
)

MODEL_NAME = "gemini-3.5-flash-lite"


# ==========================================
# 3. SOAP OUTPUT STRUCTURE
# ==========================================

SOAP_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "subjective": {
            "type": "STRING",
            "description": "Patient-reported symptoms and history."
        },
        "objective": {
            "type": "STRING",
            "description": "Observed findings and measured values."
        },
        "assessment": {
            "type": "STRING",
            "description": "Clinical assessment explicitly documented in the conversation."
        },
        "plan": {
            "type": "STRING",
            "description": "Management plan explicitly discussed."
        },
        "missing_information": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            },
            "description": "Important information not available in the conversation."
        }
    },
    "required": [
        "subjective",
        "objective",
        "assessment",
        "plan",
        "missing_information"
    ]
}


# ==========================================
# 4. GENERATE SOAP NOTES
# ==========================================

def generate_soap_notes(transcript):

    prompt = f"""
    You are MedhaJiva, an AI clinical documentation assistant.

    Analyse the following doctor-patient conversation
    and generate structured SOAP notes.

    IMPORTANT RULES:

    1. Use only information present in the transcript.
    2. Never invent symptoms, diagnoses, vital signs,
       examination findings or treatments.
    3. Distinguish patient-reported information from
       objectively observed information.
    4. If information is missing, explicitly mention it.
    5. Do not assume that an unmentioned symptom is absent.
    6. Do not turn a possible condition into a confirmed diagnosis.
    7. If the speaker or source of information is unclear,
       mention that uncertainty.
    8. Preserve important medical details.

    SOAP SECTIONS:

    S - Subjective:
    Patient-reported symptoms, history, duration and complaints.

    O - Objective:
    Measured vital signs, examination findings and observations.
    If none are documented, clearly state that.

    A - Assessment:
    The clinician's assessment if explicitly documented.
    Otherwise state that a definitive assessment is not documented.

    P - Plan:
    Tests, treatment, advice and follow-up explicitly discussed.
    Do not invent recommendations.

    Missing Information:
    List important clinical information that was not provided.

    This is a documentation task, not an autonomous diagnosis.

    CONVERSATION TRANSCRIPT:

    {transcript}
    """

    try:

        print("Sending request to Gemini...")

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SOAP_SCHEMA,
                temperature=0.2
            )
        )

        print("Gemini response received!")

        return json.loads(response.text)


    except Exception as e:

        print("\nError generating SOAP notes:")
        print(e)

        return None