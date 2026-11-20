# MedhāJīva (मेधाजीव) 🩺

**MedhāJīva** is an AI-powered clinical documentation and clinical decision support system designed to assist healthcare professionals by converting spoken doctor-patient consultations into structured medical records in real time.

---

## 🌟 Key Features

1. **Speech-to-Text Transcription**: Powered by **OpenAI Whisper** for offline, high-accuracy multi-lingual consultation transcription.
2. **Automated SOAP Notes**: Powered by **Google Gemini API** (`gemini-3.5-flash-lite`) to generate structured clinical records:
   - **S**ubjective (Patient symptoms & history)
   - **O**bjective (Vitals, observations & physical findings)
   - **A**ssessment (Clinical impressions)
   - **P**lan (Prescriptions, management & follow-ups)
   - **Missing Information Warnings** (Flags missing vital signs or unclear data)
3. **Structured Symptom Extraction**: Extracts symptoms with explicit status (`present`, `denied`, `unclear`), duration, severity, and supporting evidence.
4. **Clinical Decision Support (CDS)**: Rule-based differential condition matching and red-flag alerts based on a clinical knowledge base.
5. **Electronic Health Records (EHR)**: Built-in SQLite database tracking patients, historical consultations, and physician review states.
6. **Dual Interface**:
   - **Streamlit Web Dashboard**: Interactive, real-time UI with light/dark modes.
   - **FastAPI REST Server**: Automated endpoints and interactive OpenAPI/Swagger docs for external EHR integration.

---

## 📁 Project Architecture

```text
MedhaJiva/
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules (protects credentials & DB)
├── api.py                      # Centralized FastAPI REST server & Python API hub
├── app.py                      # Streamlit application (v1)
├── app_v2.py                   # Streamlit application (v2)
├── app_v3.py                   # Modernized Streamlit dashboard (v3 - Recommended)
├── clinical_decision_support.py# Rule-based clinical condition matching
├── clinical_knowledge_base.json# Clinical reference dataset
├── database.py                 # SQLite database models & queries
├── requirements.txt            # Python dependencies
├── soap_generator.py           # Gemini-powered SOAP note generator
├── symptom_extractor.py        # Gemini-powered symptom parser
├── transcribe.py               # Whisper audio transcription pipeline
└── assets/                     # UI logos and static resources
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/RutvikMhaske720/medical.git
cd medical
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free API key at [Google AI Studio](https://aistudio.google.com/))*

---

## 🖥️ Running the Application

### Launch the Streamlit Web Application
```bash
streamlit run app_v3.py
```
Open your browser at **`http://localhost:8501`**.

### Launch the FastAPI REST Server
```bash
python api.py
```
* API Server: **`http://localhost:8000`**
* Interactive Swagger Docs: **`http://localhost:8000/docs`**
* Alternative ReDoc: **`http://localhost:8000/redoc`**

---

## 🔒 Security & Privacy
* Real patient databases (`*.db`) and `.env` credentials are excluded by `.gitignore` to prevent data leakage.
* Educational & clinical research prototype — not intended as an autonomous diagnostic tool.
