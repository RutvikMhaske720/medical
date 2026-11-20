"""
MedhaJiva Centralized API Module & REST Server
===============================================
Combines and exposes all core MedhaJiva intelligence and database services:
1. Speech-to-Text Audio Transcription (OpenAI Whisper)
2. SOAP Clinical Notes Generation (Google Gemini API)
3. Structured Symptom Extraction (Google Gemini API)
4. Clinical Decision Support & Condition Matching
5. Patient & Consultation Records Management

Can be imported directly as Python functions or launched as a FastAPI REST API:
    python api.py
or
    uvicorn api:app --reload --port 8000
"""

import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment configuration
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# Core MedhaJiva modules
from soap_generator import generate_soap_notes
from symptom_extractor import extract_symptoms
from clinical_decision_support import match_conditions
from database import (
    initialize_database,
    add_patient,
    save_consultation,
    get_all_patients,
    get_patient_consultations,
    update_review_status,
)

# Initialize database on module load
initialize_database()

# Cached Whisper model
_whisper_model = None


# ============================================================================
# 1. PYTHON API CALLABLE FUNCTIONS
# ============================================================================

def api_transcribe_audio(audio_path_or_bytes, model_size: str = "tiny") -> Dict[str, Any]:
    """Transcribe audio file or audio bytes using OpenAI Whisper."""
    global _whisper_model
    import whisper

    if _whisper_model is None:
        _whisper_model = whisper.load_model(model_size)

    temp_file_path = None
    try:
        if isinstance(audio_path_or_bytes, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_path_or_bytes)
                temp_file_path = tmp.name
            path_to_transcribe = temp_file_path
        else:
            path_to_transcribe = str(audio_path_or_bytes)

        if not os.path.exists(path_to_transcribe):
            raise FileNotFoundError(f"Audio file not found: {path_to_transcribe}")

        result = _whisper_model.transcribe(path_to_transcribe, fp16=False)
        return {
            "transcript": result.get("text", "").strip(),
            "language": result.get("language", "")
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


def api_generate_soap(transcript: str) -> Dict[str, Any]:
    """Generate structured SOAP clinical notes from conversation transcript."""
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")
    notes = generate_soap_notes(transcript)
    if notes is None:
        raise RuntimeError("SOAP generation failed. Check GEMINI_API_KEY and input.")
    return notes


def api_extract_symptoms(transcript: str) -> Dict[str, Any]:
    """Extract structured symptoms from doctor-patient transcript."""
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")
    return extract_symptoms(transcript)


def api_match_conditions(symptoms: List[str]) -> List[Dict[str, Any]]:
    """Match identified symptoms against clinical knowledge base rules."""
    return match_conditions(symptoms)


def api_process_consultation(
    transcript: str,
    patient_id: Optional[int] = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    End-to-end clinical consultation processing:
    1. Generates SOAP notes
    2. Extracts symptoms
    3. Runs Clinical Decision Support matching
    4. Optionally persists consultation to medhajiva.db
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    soap = api_generate_soap(transcript)
    symptoms_data = api_extract_symptoms(transcript)
    symptom_list = symptoms_data.get("symptoms", [])

    # Filter present symptoms for decision support
    present_symptoms = [
        s.get("symptom", "")
        for s in symptom_list
        if s.get("status") == "present" and s.get("symptom")
    ]
    clinical_matches = api_match_conditions(present_symptoms)

    consultation_id = None
    if save_to_db and patient_id is not None:
        consultation_id = save_consultation(
            patient_id=patient_id,
            transcript=transcript,
            soap_note=soap,
            symptoms=symptom_list
        )

    return {
        "consultation_id": consultation_id,
        "patient_id": patient_id,
        "soap": soap,
        "symptoms": symptom_list,
        "clinical_matches": clinical_matches
    }


# ============================================================================
# 2. FASTAPI REST SERVER & ENDPOINTS
# ============================================================================

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="MedhaJiva AI Clinical Assistant API",
        description="Unified REST API for Clinical Documentation, Speech Transcription, and Decision Support.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------ Request Schemas ------------------

    class TranscriptRequest(BaseModel):
        transcript: str = Field(..., description="Doctor-patient conversation text")

    class ConditionsRequest(BaseModel):
        symptoms: List[str] = Field(..., description="List of present symptoms")

    class PatientCreate(BaseModel):
        name: str
        age: int
        gender: str
        contact: Optional[str] = ""

    class ProcessConsultationRequest(BaseModel):
        transcript: str
        patient_id: Optional[int] = None
        save_to_db: bool = False

    class UpdateStatusRequest(BaseModel):
        consultation_id: int
        new_status: str = Field(..., description="Pending | Reviewed | Needs Correction")

    # ------------------ Endpoints ------------------

    @app.get("/health", tags=["System"])
    def health_check():
        """Health check endpoint."""
        api_key_set = bool(os.getenv("GEMINI_API_KEY"))
        return {
            "status": "healthy",
            "service": "MedhaJiva API",
            "gemini_api_key_configured": api_key_set
        }

    @app.post("/api/transcribe", tags=["Speech-to-Text"])
    async def transcribe_audio_endpoint(
        file: UploadFile = File(...),
        model: str = Form("tiny")
    ):
        """Upload an audio file (.wav, .mp3, .m4a) and receive the transcribed text."""
        try:
            content = await file.read()
            result = api_transcribe_audio(content, model_size=model)
            return {"filename": file.filename, **result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/soap", tags=["Clinical Documentation"])
    def generate_soap_endpoint(request: TranscriptRequest):
        """Generate structured SOAP clinical notes from conversation transcript."""
        try:
            notes = api_generate_soap(request.transcript)
            return {"status": "success", "data": notes}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/symptoms", tags=["Symptom Extraction"])
    def extract_symptoms_endpoint(request: TranscriptRequest):
        """Extract present, denied, and unclear symptoms with duration and severity."""
        try:
            symptoms = api_extract_symptoms(request.transcript)
            return {"status": "success", "data": symptoms}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/match-conditions", tags=["Decision Support"])
    def match_conditions_endpoint(request: ConditionsRequest):
        """Match extracted symptoms against clinical rules."""
        try:
            matches = api_match_conditions(request.symptoms)
            return {"status": "success", "matches": matches}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/consultations/process", tags=["Pipeline"])
    def process_consultation_endpoint(request: ProcessConsultationRequest):
        """Execute end-to-end pipeline: SOAP generation + Symptom extraction + CDS matching."""
        try:
            result = api_process_consultation(
                transcript=request.transcript,
                patient_id=request.patient_id,
                save_to_db=request.save_to_db
            )
            return {"status": "success", "data": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/patients", tags=["Database"])
    def list_patients():
        """Get all registered patients."""
        try:
            patients = get_all_patients()
            return {"status": "success", "patients": [dict(p) for p in patients]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/patients", tags=["Database"])
    def create_patient(patient: PatientCreate):
        """Register a new patient."""
        try:
            patient_id = add_patient(
                name=patient.name,
                age=patient.age,
                gender=patient.gender,
                contact=patient.contact or ""
            )
            return {"status": "success", "patient_id": patient_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/consultations/{patient_id}", tags=["Database"])
    def get_consultations(patient_id: int):
        """Retrieve all recorded consultations for a patient."""
        try:
            consultations = get_patient_consultations(patient_id)
            cleaned = []
            for c in consultations:
                item = dict(c)
                # Parse JSON fields if string
                for json_col in ("soap_notes", "symptoms"):
                    if isinstance(item.get(json_col), str):
                        try:
                            item[json_col] = json.loads(item[json_col])
                        except json.JSONDecodeError:
                            pass
                cleaned.append(item)
            return {"status": "success", "consultations": cleaned}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/consultations/status", tags=["Database"])
    def update_status(payload: UpdateStatusRequest):
        """Update physician review status of a consultation."""
        try:
            update_review_status(payload.consultation_id, payload.new_status)
            return {
                "status": "success",
                "consultation_id": payload.consultation_id,
                "review_status": payload.new_status
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

else:
    app = None


# ============================================================================
# 3. DIRECT EXECUTION / TEST RUN
# ============================================================================

if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        port = int(os.getenv("API_PORT", 8000))
        host = os.getenv("API_HOST", "0.0.0.0")
        print(f"Starting MedhaJiva API Server on http://{host}:{port}")
        print(f"Interactive Swagger Docs: http://localhost:{port}/docs")
        uvicorn.run("api:app", host=host, port=port, reload=True)
    else:
        print("FastAPI is not installed. To run the REST server, install fastapi and uvicorn:")
        print("    pip install fastapi uvicorn")
