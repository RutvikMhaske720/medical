import streamlit as st
import whisper
import os
import tempfile
from pathlib import Path
from soap_generator import generate_soap_notes
from symptom_extractor import extract_symptoms
from clinical_decision_support import match_conditions
from database import (
    initialize_database,
    add_patient,
    save_consultation,
    get_all_patients,
    get_patient_consultations,
    update_review_status
)


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="MedhaJiva",
    page_icon="🩺",
    layout="wide"
)


# ==========================================
# CUSTOM UI THEME
# ==========================================

st.markdown("""
<style>

/* Main application background */
.stApp {
    background: linear-gradient(
        135deg,
        #f4f7fb 0%,
        #eef3f9 50%,
        #f7f9fc 100%
    );
    color: #172f4d;
}

/* Main content area */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Main headings */
h1 {
    color: #172f4d !important;
    font-weight: 750 !important;
    letter-spacing: -1px;
}

h2, h3 {
    color: #203b59 !important;
    font-weight: 650 !important;
}

/* Paragraphs and normal text */
p, label, .stMarkdown {
    color: #40536b;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.78);
    border-right: 1px solid rgba(160, 180, 205, 0.25);
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(
        135deg,
        #315f91,
        #4d9de0
    );
    color: white !important;
    border: none;
    border-radius: 12px;
    padding: 0.55rem 1.2rem;
    font-weight: 600;
    transition: all 0.25s ease;
    box-shadow: 0 4px 12px rgba(49, 95, 145, 0.15);
}

/* Button hover animation */
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 7px 18px rgba(49, 95, 145, 0.25);
    border: none;
}

/* Button press animation */
.stButton > button:active,
.stDownloadButton > button:active,
.stFormSubmitButton > button:active {
    transform: scale(0.97);
}

/* Input fields */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] {
    border-radius: 10px;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.65);
    border: 1px dashed #9bb6d1;
    border-radius: 16px;
    padding: 12px;
}

/* Expanders */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(160, 180, 205, 0.3);
    border-radius: 14px;
    overflow: hidden;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 12px;
}

/* Dividers */
hr {
    border-color: rgba(160, 180, 205, 0.35);
}

/* Subtle animation when content appears */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.block-container {
    animation: fadeIn 0.45s ease-out;
}

</style>
""", unsafe_allow_html=True)
# --------------------------------------------------------

initialize_database()

if "soap_note" not in st.session_state:
    st.session_state.soap_note = None

if "soap_source" not in st.session_state:
    st.session_state.soap_source = ""

if "symptom_results" not in st.session_state:
    st.session_state.symptom_results = None

if "symptom_source" not in st.session_state:
    st.session_state.symptom_source = ""

if "clinical_results" not in st.session_state:
    st.session_state.clinical_results = None

if "clinical_source" not in st.session_state:
    st.session_state.clinical_source = ""

if "saved_consultation_id" not in st.session_state:
    st.session_state.saved_consultation_id = None


# ==========================================
# 2. LOAD WHISPER MODEL
# ==========================================

@st.cache_resource
def load_whisper_model():

    return whisper.load_model("tiny")


# ==========================================
# 3. APPLICATION HEADER
# ==========================================

st.title("🩺 MedhaJiva")

st.subheader("AI-Powered Clinical Assistant")

st.write(
    "Transform doctor-patient conversations "
    "into structured clinical documentation."
)

st.divider()


# ==========================================
# 4. AUDIO UPLOAD
# ==========================================

st.header("Audio Transcription")

uploaded_file = st.file_uploader(
    "Upload consultation recording",
    type=["wav", "mp3", "m4a", "mpeg", "mpga", "webm"]
)


# ==========================================
# 5. TRANSCRIPTION
# ==========================================

if "transcript_editor" not in st.session_state:
    st.session_state.transcript_editor = ""

if "detected_language" not in st.session_state:
    st.session_state.detected_language = ""


if uploaded_file is not None:

    st.success("Audio uploaded successfully!")

    st.audio(uploaded_file)

    if st.button("Generate Transcript"):

        temp_path = None

        try:

            with st.spinner("Loading Whisper model..."):

                model = load_whisper_model()

            with st.spinner("Transcribing audio... Please wait."):

                suffix = Path(uploaded_file.name).suffix

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix
                ) as temp_audio:

                    temp_audio.write(uploaded_file.getbuffer())
                    temp_path = temp_audio.name

                result = model.transcribe(
                    temp_path,
                    fp16=False
                )

                st.session_state.transcript_editor = (
                    result["text"].strip()
                )

                st.session_state.detected_language = (
                    result.get("language", "Unknown")
                )

            st.success("Transcription completed!")

        except Exception as e:

            st.error(f"Transcription failed: {e}")

        finally:

            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


# ==========================================
# 6. DISPLAY TRANSCRIPT
# ==========================================

if st.session_state.transcript_editor:

    st.divider()

    st.header("Generated Transcript")

    st.caption(
        f"Detected language: "
        f"{st.session_state.detected_language}"
    )

    edited_transcript = st.text_area(
        "Review and edit the transcript:",
        key="transcript_editor",
        height=250
    )


    # ======================================
    # 7. SAVE TRANSCRIPT
    # ======================================

    if st.button("Save Transcript"):

        os.makedirs("output", exist_ok=True)

        with open(
            "output/transcript.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write(edited_transcript)

        st.success("Transcript saved successfully!")


    # ======================================
    # 8. DOWNLOAD TRANSCRIPT
    # ======================================

    st.download_button(
        label="Download Transcript",
        data=edited_transcript,
        file_name="transcript.txt",
        mime="text/plain"
    )


    # ======================================
    # 9. SOAP NOTE GENERATION
    # ======================================

    st.divider()

    st.header("Clinical Documentation")

    if st.button("Generate SOAP Notes"):

        transcript = st.session_state.transcript_editor.strip()

        if not transcript:

            st.warning("Transcript is empty.")

        else:

            try:

                with st.spinner("Generating SOAP notes using Gemini..."):

                    soap = generate_soap_notes(transcript)

                    st.session_state.soap_note = soap
                    st.session_state.soap_source = transcript

                st.success("SOAP notes generated successfully!")

            except Exception as e:

                st.error(f"SOAP generation failed: {e}")


    # ======================================
    # 10. DISPLAY SOAP NOTES
    # ======================================

    if (
        st.session_state.soap_note
        and st.session_state.soap_source
        == st.session_state.transcript_editor
    ):

        soap = st.session_state.soap_note

        st.subheader("S - Subjective")
        st.write(soap["subjective"])

        st.subheader("O - Objective")
        st.write(soap["objective"])

        st.subheader("A - Assessment")
        st.write(soap["assessment"])

        st.subheader("P - Plan")
        st.write(soap["plan"])

        st.subheader("Missing Information")

        for item in soap["missing_information"]:

            st.write(f"- {item}")

        st.caption(
            "AI-generated documentation. "
            "Requires review and approval by a qualified clinician."
        )

    
    # ======================================
    # SYMPTOM EXTRACTION
    # ======================================

    st.divider()

    st.header("Symptom Extraction")

    if st.button("Extract Symptoms"):

        transcript = st.session_state.transcript_editor.strip()

        if not transcript:

            st.warning("Transcript is empty.")

        else:

            try:

                with st.spinner("Extracting symptoms..."):

                    symptoms = extract_symptoms(transcript)

                    st.session_state.symptom_results = symptoms
                    st.session_state.symptom_source = transcript

                st.success("Symptoms extracted successfully!")

            except Exception as e:

                st.error(f"Symptom extraction failed: {e}")


    # ======================================
    # DISPLAY EXTRACTED SYMPTOMS
    # ======================================

    if (
        st.session_state.symptom_results
        and st.session_state.symptom_source
        == st.session_state.transcript_editor
    ):

        symptoms = st.session_state.symptom_results["symptoms"]

        if symptoms:

            for item in symptoms:

                st.subheader(item["symptom"])

                st.write("Status:", item["status"])
                st.write("Duration:", item["duration"])
                st.write("Severity:", item["severity"])
                st.write("Evidence:", item["evidence"])

                st.divider()

        else:

            st.info("No symptoms were identified.")

        st.caption(
            "AI-extracted information. "
            "Requires clinician verification."
        )
    

    # ======================================
    # CLINICAL DECISION SUPPORT
    # ======================================

    st.divider()

    st.header("Clinical Decision Support")

    current_transcript = st.session_state.transcript_editor

    # Check whether symptoms were extracted
    # from the current transcript

    if (
        st.session_state.symptom_results is not None
        and st.session_state.symptom_source == current_transcript
    ):

        if st.button("Find Possible Condition Associations"):

            try:

                with st.spinner("Comparing symptoms with knowledge base..."):

                    extracted = st.session_state.symptom_results["symptoms"]

                    results = match_conditions(extracted)

                    st.session_state.clinical_results = results
                    st.session_state.clinical_source = current_transcript

                st.success("Symptom matching completed!")

            except Exception as e:

                st.error(f"Matching failed: {e}")

    else:

        st.info(
            "Generate symptoms from the current transcript first."
        )


    # ======================================
    # DISPLAY MATCHING RESULTS
    # ======================================

    if (
        st.session_state.clinical_results is not None
        and st.session_state.clinical_source == current_transcript
    ):

        results = st.session_state.clinical_results

        st.subheader("Possible Condition Associations")

        if results:

            for item in results:

                with st.expander(item["name"], expanded=True):

                    st.write(
                        "**Matching symptoms:**",
                        ", ".join(item["matched_symptoms"])
                    )

                    st.write(
                        "**Number of matching symptoms:**",
                        item["match_count"]
                    )

                    if item["denied_symptoms"]:

                        st.write(
                            "**Explicitly denied symptoms also associated with this condition:**",
                            ", ".join(item["denied_symptoms"])
                        )

                    else:

                        st.write(
                            "**Explicitly denied associated symptoms:** None identified"
                        )

                    st.write("**Limitations:**", item["limitations"])

                    st.markdown(
                        f"[View medical reference]({item['source']})"
                    )

                    st.divider()

        else:

            st.warning(
                "No condition associations were found "
                "for the present symptoms."
            )

        st.caption(
            "Educational prototype only. These associations are "
            "not diagnoses or estimates of disease probability. "
            "A qualified clinician must review all findings."
        )


    # ======================================
    # PATIENT REGISTRATION & DATABASE
    # ======================================

    st.divider()

    st.header("Patient & Consultation Records")

    patients = get_all_patients()

    # Choose new or existing patient

    patient_options = ["Register New Patient"]

    if patients:
        patient_options.append("Select Existing Patient")

    with st.form("consultation_save_form"):

        patient_mode = st.radio(
            "Patient Record",
            patient_options
        )

        patient_name = None
        patient_age = None
        selected_patient_id = None

        if patient_mode == "Register New Patient":

            patient_name = st.text_input(
                "Patient Name (optional)"
            )

            age_input = st.text_input(
                "Patient Age (optional)"
            )

        else:

            selected_patient_id = st.selectbox(
                "Select Patient",
                options=[
                    p["patient_id"] for p in patients
                ],
                format_func=lambda pid: next(
                    f'{p["name"] or "Unnamed Patient"} '
                    f'(ID: {p["patient_id"]})'
                    for p in patients
                    if p["patient_id"] == pid
                )
            )

        save_button = st.form_submit_button(
            "Save Consultation"
        )

    # ======================================
    # SAVE RECORD
    # ======================================

    if save_button:

        try:

            # Register new patient

            if patient_mode == "Register New Patient":

                age_text = age_input.strip()

                if age_text:

                    if not age_text.isdigit():

                        st.error("Age must be a whole number.")

                        st.stop()

                    patient_age = int(age_text)

                    if not 0 <= patient_age <= 120:

                        st.error("Enter an age between 0 and 120.")

                        st.stop()

                patient_id = add_patient(
                    name=patient_name.strip() or None,
                    age=patient_age
                )

            else:

                patient_id = selected_patient_id

            # Only save outputs belonging to
            # the current transcript

            current_transcript = (
                st.session_state.transcript_editor.strip()
            )

            soap_data = None
            symptom_data = None
            clinical_data = None

            if (
                st.session_state.soap_note is not None
                and st.session_state.soap_source
                == current_transcript
            ):

                soap_data = st.session_state.soap_note

            if (
                st.session_state.symptom_results is not None
                and st.session_state.symptom_source
                == current_transcript
            ):

                symptom_data = (
                    st.session_state.symptom_results["symptoms"]
                )

            if (
                st.session_state.clinical_results is not None
                and st.session_state.clinical_source
                == current_transcript
            ):

                clinical_data = st.session_state.clinical_results

            # Save consultation in SQLite

            consultation_id = save_consultation(

                patient_id=patient_id,

                transcript=current_transcript,

                soap_notes=soap_data,

                symptoms=symptom_data,

                clinical_results=clinical_data

            )

            st.session_state.saved_consultation_id = (
                consultation_id
            )

            st.success("Consultation saved successfully!")

            st.write("Patient ID:", patient_id)

            st.write(
                "Consultation ID:",
                consultation_id
            )

            st.info("Review Status: Pending")

        except Exception as e:

            st.error(f"Database error: {e}")





# ======================================
# PATIENT RECORDS & CONSULTATION HISTORY
# ======================================

st.divider()

st.header("Patient Records & History")

patients = get_all_patients()

if not patients:

    st.info("No patient records found.")

else:

    # Select patient

    patient_options = {
         f'{p["name"] or "Unnamed Patient"} '
         f'(ID: {p["patient_id"]})': p["patient_id"]
         for p in patients
    }

    selected_label = st.selectbox(
         "Search and select a patient",
         options=list(patient_options.keys()),
         key="history_patient_selector"
    )

    selected_patient_id = patient_options[selected_label]

        # Find selected patient details

    selected_patient = next(
         p for p in patients
         if p["patient_id"] == selected_patient_id
    )

    st.subheader("Patient Details")

    col1, col2 = st.columns(2)

    with col1:

        st.write("**Patient ID:**", selected_patient["patient_id"])

        st.write(
             "**Patient Name:**",
             selected_patient["name"] or "Not provided"
        )

    with col2:

        st.write(
             "**Age:**",
             selected_patient["age"]
             if selected_patient["age"] is not None
             else "Not provided"
        )

        # Retrieve consultation history

    records = get_patient_consultations(
         selected_patient_id
    )

    st.divider()

    st.subheader("Consultation History")

    if not records:

         st.info("No consultations found for this patient.")

    else:

         st.write("Total consultations:", len(records))

         for record in records:

                consultation_id = record["consultation_id"]

                with st.expander(
                    f'Consultation #{consultation_id} '
                    f'| {record["consultation_date"]} '
                    f'| {record["review_status"]}'
                ):

                    st.write(
                        "**Review Status:**",
                        record["review_status"]
                    )

                    # Transcript

                    st.markdown("### Transcript")

                    st.text(record["transcript"])

                    # SOAP notes

                    st.markdown("### SOAP Notes")

                    if record["soap_notes"]:

                        soap = record["soap_notes"]

                        st.write("**Subjective:**", soap["subjective"])

                        st.write("**Objective:**", soap["objective"])

                        st.write("**Assessment:**", soap["assessment"])

                        st.write("**Plan:**", soap["plan"])

                        st.write("**Missing Information:**")

                        for item in soap["missing_information"]:

                            st.write("-", item)

                    else:

                        st.info("SOAP notes were not saved.")

                    # Symptoms

                    st.markdown("### Extracted Symptoms")

                    if record["symptoms"]:

                        for item in record["symptoms"]:

                            st.write(
                                f'- {item["symptom"]} '
                                f'({item["status"]})'
                            )

                    else:

                        st.info("No symptoms were saved.")

                    # Clinical results

                    st.markdown("### Condition Associations")

                    if record["clinical_results"]:

                        for item in record["clinical_results"]:

                            st.write("**", item["name"], "**")

                            st.write(
                                "Matched symptoms:",
                                ", ".join(item["matched_symptoms"])
                            )

                            st.markdown(
                                f'[Medical reference]({item["source"]})'
                            )

                    else:

                        st.info(
                            "No condition associations were saved."
                        )

                    st.divider()

                    # Update review status

                    st.markdown("### Clinician Review")

                    with st.form(
                        f"review_form_{consultation_id}"
                    ):

                        new_status = st.selectbox(
                            "Update review status",
                            [
                                "Pending",
                                "Reviewed",
                                "Needs Correction"
                            ],
                            index=[
                                "Pending",
                                "Reviewed",
                                "Needs Correction"
                            ].index(record["review_status"]),
                            key=f"review_status_{consultation_id}"
                        )

                        update_button = st.form_submit_button(
                            "Update Status"
                        )

                        if update_button:

                            try:

                                update_review_status(
                                    consultation_id,
                                    new_status
                                )

                                st.success(
                                    "Review status updated!"
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    f"Status update failed: {e}"
                                )


# ==========================================
# 11. FOOTER
# ==========================================

st.divider()

st.caption(
    "MedhaJiva | AI Clinical Assistant | "
    "Educational prototype — not for clinical diagnosis."
)
