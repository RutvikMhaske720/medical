import streamlit as st
import whisper
import os
import tempfile
import pandas as pd
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

initialize_database()

# Session state (same keys as app.py)

defaults = {
    "soap_note": None,
    "soap_source": "",
    "symptom_results": None,
    "symptom_source": "",
    "clinical_results": None,
    "clinical_source": "",
    "saved_consultation_id": None,
    "transcript_editor": "",
    "detected_language": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# 2. HELPERS
# ==========================================

REVIEW_OPTIONS = ["Pending", "Reviewed", "Needs Correction"]

STATUS_ICON = {
    "Pending": "🟡",
    "Reviewed": "🟢",
    "Needs Correction": "🔴",
}


@st.cache_resource
def load_whisper_model():

    return whisper.load_model("tiny")


def current_transcript():

    return st.session_state.transcript_editor.strip()


def soap_is_current():

    return (
        st.session_state.soap_note is not None
        and st.session_state.soap_source == current_transcript()
    )


def symptoms_are_current():

    return (
        st.session_state.symptom_results is not None
        and st.session_state.symptom_source == current_transcript()
    )


def clinical_is_current():

    return (
        st.session_state.clinical_results is not None
        and st.session_state.clinical_source == current_transcript()
    )


def symptom_status_icon(status):

    text = str(status).strip().lower()

    if text in ("present", "positive", "yes"):
        return "🔴 " + str(status)

    if text in ("denied", "absent", "negative", "no"):
        return "⚪ " + str(status)

    return "🟡 " + str(status)


def soap_to_text(soap):

    lines = [
        "SOAP NOTE",
        "=========",
        "",
        "S - SUBJECTIVE",
        str(soap["subjective"]),
        "",
        "O - OBJECTIVE",
        str(soap["objective"]),
        "",
        "A - ASSESSMENT",
        str(soap["assessment"]),
        "",
        "P - PLAN",
        str(soap["plan"]),
        "",
        "MISSING INFORMATION",
    ]

    for item in soap["missing_information"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append(
        "AI-generated documentation. "
        "Requires review and approval by a qualified clinician."
    )

    return "\n".join(lines)


# ==========================================
# 3. SIDEBAR
# ==========================================

with st.sidebar:

    st.title("🩺 MedhaJiva")
    st.caption("AI-Powered Clinical Assistant")

    st.divider()

    st.markdown("**Workflow**")
    st.markdown(
        "1. Upload audio and generate transcript\n"
        "2. Generate SOAP notes\n"
        "3. Extract symptoms\n"
        "4. Find condition associations\n"
        "5. Save the consultation\n"
        "6. Review records in History"
    )

    st.divider()

    st.warning(
        "Educational prototype. Not for clinical diagnosis. "
        "All AI output needs clinician review."
    )


# ==========================================
# 4. HEADER + PROGRESS STRIP
# ==========================================

st.title("🩺 MedhaJiva")

st.write(
    "Transform doctor-patient conversations "
    "into structured clinical documentation."
)

p1, p2, p3, p4, p5 = st.columns(5)

p1.metric(
    "Transcript",
    "✅" if current_transcript() else "⏳"
)

p2.metric(
    "SOAP Notes",
    "✅" if soap_is_current() else "⏳"
)

p3.metric(
    "Symptoms",
    "✅" if symptoms_are_current() else "⏳"
)

p4.metric(
    "Associations",
    "✅" if clinical_is_current() else "⏳"
)

p5.metric(
    "Saved",
    "✅" if st.session_state.saved_consultation_id else "⏳"
)

st.divider()


# ==========================================
# 5. TABS
# ==========================================

(
    tab_transcript,
    tab_soap,
    tab_symptoms,
    tab_cds,
    tab_save,
    tab_history
) = st.tabs([
    "🎙️ Transcript",
    "📝 SOAP Notes",
    "🔍 Symptoms",
    "🧠 Decision Support",
    "💾 Save Consultation",
    "🗂️ Patient History"
])


# ------------------------------------------
# TAB 1: AUDIO + TRANSCRIPT
# ------------------------------------------

with tab_transcript:

    st.header("Audio Transcription")

    uploaded_file = st.file_uploader(
        "Upload consultation recording",
        type=["wav", "mp3", "m4a", "mpeg", "mpga", "webm"]
    )

    if uploaded_file is not None:

        st.success("Audio uploaded successfully!")

        st.audio(uploaded_file)

        if st.button("Generate Transcript", type="primary"):

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

    if st.session_state.transcript_editor:

        st.divider()

        st.subheader("Generated Transcript")

        st.caption(
            f"Detected language: "
            f"{st.session_state.detected_language}"
        )

        edited_transcript = st.text_area(
            "Review and edit the transcript:",
            key="transcript_editor",
            height=300
        )

        b1, b2, _ = st.columns([1, 1, 3])

        with b1:

            if st.button("Save Transcript"):

                os.makedirs("output", exist_ok=True)

                with open(
                    "output/transcript.txt",
                    "w",
                    encoding="utf-8"
                ) as file:

                    file.write(edited_transcript)

                st.success("Transcript saved successfully!")

        with b2:

            st.download_button(
                label="Download Transcript",
                data=edited_transcript,
                file_name="transcript.txt",
                mime="text/plain"
            )

    else:

        st.info("Upload an audio file and generate a transcript to begin.")


# ------------------------------------------
# TAB 2: SOAP NOTES
# ------------------------------------------

with tab_soap:

    st.header("Clinical Documentation")

    has_transcript = bool(current_transcript())

    if not has_transcript:

        st.info("Generate a transcript first (Transcript tab).")

    if st.button(
        "Generate SOAP Notes",
        type="primary",
        disabled=not has_transcript
    ):

        transcript = current_transcript()

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

    if soap_is_current():

        soap = st.session_state.soap_note

        left, right = st.columns(2)

        with left:

            with st.container(border=True):
                st.markdown("#### S - Subjective")
                st.write(soap["subjective"])

            with st.container(border=True):
                st.markdown("#### A - Assessment")
                st.write(soap["assessment"])

        with right:

            with st.container(border=True):
                st.markdown("#### O - Objective")
                st.write(soap["objective"])

            with st.container(border=True):
                st.markdown("#### P - Plan")
                st.write(soap["plan"])

        with st.container(border=True):

            st.markdown("#### Missing Information")

            if soap["missing_information"]:

                for item in soap["missing_information"]:
                    st.write(f"- {item}")

            else:

                st.write("None identified.")

        st.download_button(
            label="Download SOAP Note",
            data=soap_to_text(soap),
            file_name="soap_note.txt",
            mime="text/plain"
        )

        st.warning(
            "AI-generated documentation. "
            "Requires review and approval by a qualified clinician."
        )


# ------------------------------------------
# TAB 3: SYMPTOM EXTRACTION
# ------------------------------------------

with tab_symptoms:

    st.header("Symptom Extraction")

    has_transcript = bool(current_transcript())

    if not has_transcript:

        st.info("Generate a transcript first (Transcript tab).")

    if st.button(
        "Extract Symptoms",
        type="primary",
        disabled=not has_transcript
    ):

        transcript = current_transcript()

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

    if symptoms_are_current():

        symptom_list = st.session_state.symptom_results["symptoms"]

        if symptom_list:

            rows = []

            for item in symptom_list:

                rows.append({
                    "Symptom": item.get("symptom", ""),
                    "Status": symptom_status_icon(item.get("status", "")),
                    "Duration": item.get("duration", ""),
                    "Severity": item.get("severity", ""),
                    "Evidence": item.get("evidence", ""),
                })

            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True
            )

            st.caption("🔴 present   ⚪ denied   🟡 other / unclear")

        else:

            st.info("No symptoms were identified.")

        st.warning(
            "AI-extracted information. "
            "Requires clinician verification."
        )


# ------------------------------------------
# TAB 4: CLINICAL DECISION SUPPORT
# ------------------------------------------

with tab_cds:

    st.header("Clinical Decision Support")

    if symptoms_are_current():

        if st.button(
            "Find Possible Condition Associations",
            type="primary"
        ):

            try:

                with st.spinner("Comparing symptoms with knowledge base..."):

                    extracted = st.session_state.symptom_results["symptoms"]

                    results = match_conditions(extracted)

                    st.session_state.clinical_results = results
                    st.session_state.clinical_source = current_transcript()

                st.success("Symptom matching completed!")

            except Exception as e:

                st.error(f"Matching failed: {e}")

    else:

        st.info(
            "Extract symptoms from the current transcript first "
            "(Symptoms tab)."
        )

    if clinical_is_current():

        results = st.session_state.clinical_results

        st.subheader("Possible Condition Associations")

        if results:

            for item in results:

                with st.expander(
                    f'{item["name"]}  ·  '
                    f'{item["match_count"]} matching symptom(s)',
                    expanded=True
                ):

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

        else:

            st.warning(
                "No condition associations were found "
                "for the present symptoms."
            )

        st.warning(
            "Educational prototype only. These associations are "
            "not diagnoses or estimates of disease probability. "
            "A qualified clinician must review all findings."
        )


# ------------------------------------------
# TAB 5: SAVE CONSULTATION
# ------------------------------------------

with tab_save:

    st.header("Save Consultation")

    if not current_transcript():

        st.info("Generate a transcript first (Transcript tab).")

    else:

        patients = get_all_patients()

        patient_options = ["Register New Patient"]

        if patients:
            patient_options.append("Select Existing Patient")

        # Radio sits outside the form so the fields below
        # switch immediately when the choice changes.

        patient_mode = st.radio(
            "Patient Record",
            patient_options,
            horizontal=True,
            key="patient_mode"
        )

        # What will be saved

        s1, s2, s3 = st.columns(3)

        s1.write("SOAP notes: " + ("✅" if soap_is_current() else "➖ not generated"))
        s2.write("Symptoms: " + ("✅" if symptoms_are_current() else "➖ not extracted"))
        s3.write("Associations: " + ("✅" if clinical_is_current() else "➖ not generated"))

        with st.form("consultation_save_form"):

            patient_name = ""
            age_input = ""
            selected_patient_id = None

            if patient_mode == "Register New Patient":

                f1, f2 = st.columns(2)

                with f1:
                    patient_name = st.text_input(
                        "Patient Name (optional)"
                    )

                with f2:
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
                "Save Consultation",
                type="primary"
            )

        if save_button:

            patient_age = None
            error_message = None

            if patient_mode == "Register New Patient":

                age_text = (age_input or "").strip()

                if age_text:

                    if not age_text.isdigit():

                        error_message = "Age must be a whole number."

                    else:

                        patient_age = int(age_text)

                        if not 0 <= patient_age <= 120:

                            error_message = (
                                "Enter an age between 0 and 120."
                            )

            if error_message:

                st.error(error_message)

            else:

                try:

                    if patient_mode == "Register New Patient":

                        patient_id = add_patient(
                            name=(patient_name or "").strip() or None,
                            age=patient_age
                        )

                    else:

                        patient_id = selected_patient_id

                    # Only save outputs belonging to
                    # the current transcript

                    transcript_to_save = current_transcript()

                    soap_data = None
                    symptom_data = None
                    clinical_data = None

                    if soap_is_current():

                        soap_data = st.session_state.soap_note

                    if symptoms_are_current():

                        symptom_data = (
                            st.session_state.symptom_results["symptoms"]
                        )

                    if clinical_is_current():

                        clinical_data = st.session_state.clinical_results

                    consultation_id = save_consultation(

                        patient_id=patient_id,

                        transcript=transcript_to_save,

                        soap_notes=soap_data,

                        symptoms=symptom_data,

                        clinical_results=clinical_data

                    )

                    st.session_state.saved_consultation_id = (
                        consultation_id
                    )

                    st.success("Consultation saved successfully!")

                    r1, r2 = st.columns(2)

                    r1.metric("Patient ID", patient_id)
                    r2.metric("Consultation ID", consultation_id)

                    st.info("Review Status: Pending")

                except Exception as e:

                    st.error(f"Database error: {e}")


# ------------------------------------------
# TAB 6: PATIENT HISTORY
# ------------------------------------------

with tab_history:

    st.header("Patient Records & History")

    patients = get_all_patients()

    if not patients:

        st.info("No patient records found.")

    else:

        search_text = st.text_input(
            "🔎 Search patients by name or ID",
            key="history_search"
        ).strip().lower()

        if search_text:

            filtered_patients = [
                p for p in patients
                if search_text in (p["name"] or "").lower()
                or search_text in str(p["patient_id"]).lower()
            ]

        else:

            filtered_patients = patients

        if not filtered_patients:

            st.warning("No patients match your search.")

        else:

            patient_lookup = {
                f'{p["name"] or "Unnamed Patient"} '
                f'(ID: {p["patient_id"]})': p["patient_id"]
                for p in filtered_patients
            }

            selected_label = st.selectbox(
                "Select a patient",
                options=list(patient_lookup.keys()),
                key="history_patient_selector"
            )

            history_patient_id = patient_lookup[selected_label]

            selected_patient = next(
                p for p in patients
                if p["patient_id"] == history_patient_id
            )

            with st.container(border=True):

                st.subheader("Patient Details")

                d1, d2, d3 = st.columns(3)

                d1.metric("Patient ID", selected_patient["patient_id"])

                d2.metric(
                    "Name",
                    selected_patient["name"] or "Not provided"
                )

                d3.metric(
                    "Age",
                    selected_patient["age"]
                    if selected_patient["age"] is not None
                    else "Not provided"
                )

            records = get_patient_consultations(history_patient_id)

            st.subheader("Consultation History")

            if not records:

                st.info("No consultations found for this patient.")

            else:

                st.write("Total consultations:", len(records))

                for record in records:

                    consultation_id = record["consultation_id"]

                    icon = STATUS_ICON.get(record["review_status"], "⚪")

                    with st.expander(
                        f'{icon} Consultation #{consultation_id} '
                        f'| {record["consultation_date"]} '
                        f'| {record["review_status"]}'
                    ):

                        (
                            h_transcript,
                            h_soap,
                            h_symptoms,
                            h_assoc,
                            h_review
                        ) = st.tabs([
                            "Transcript",
                            "SOAP",
                            "Symptoms",
                            "Associations",
                            "Review"
                        ])

                        with h_transcript:

                            st.text(record["transcript"])

                        with h_soap:

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

                        with h_symptoms:

                            if record["symptoms"]:

                                for item in record["symptoms"]:

                                    st.write(
                                        f'- {item["symptom"]} '
                                        f'({item["status"]})'
                                    )

                            else:

                                st.info("No symptoms were saved.")

                        with h_assoc:

                            if record["clinical_results"]:

                                for item in record["clinical_results"]:

                                    st.markdown(f'**{item["name"]}**')

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

                        with h_review:

                            st.write(
                                "**Current status:**",
                                f'{icon} {record["review_status"]}'
                            )

                            with st.form(
                                f"review_form_{consultation_id}"
                            ):

                                if record["review_status"] in REVIEW_OPTIONS:
                                    status_index = REVIEW_OPTIONS.index(
                                        record["review_status"]
                                    )
                                else:
                                    status_index = 0

                                new_status = st.selectbox(
                                    "Update review status",
                                    REVIEW_OPTIONS,
                                    index=status_index,
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
# 6. FOOTER
# ==========================================

st.divider()

st.caption(
    "MedhaJiva | AI Clinical Assistant | "
    "Educational prototype — not for clinical diagnosis."
)