import streamlit as st
import whisper
import os
import tempfile
import html as html_lib
import base64
import pandas as pd
from datetime import datetime
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
    page_title="MedhāJīva",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

initialize_database()

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
# 2. STYLING (CSS)
# ==========================================

# Initial theme follows Streamlit's own theme when it is available.

if "dark_mode" not in st.session_state:

    try:
        st.session_state.dark_mode = (st.context.theme.type == "dark")
    except Exception:
        st.session_state.dark_mode = False

DARK = bool(st.session_state.dark_mode)

PALETTES = {
    "light": {
        "bg": "#F2F4F9",
        "card": "#FFFFFF",
        "text": "#111827",
        "muted": "#5B6475",
        "line": "#E3E8F0",
        "soft": "#F5F7FB",
        "softblue": "#EEF3FF",
        "input": "#FFFFFF",
        "track": "#E9EDF4",
        "shadow": "0 8px 30px rgba(17, 24, 39, 0.07)",
        "primary": "#2F6BFF",
        "primarydark": "#1E4FD8",
        "stageicon": "#EEF2F7",
        "stageiconfg": "#8B95A7",
        "donebg": "#E3F6EB",
        "donefg": "#16A34A",
    },
    "dark": {
        "bg": "#0C111D",
        "card": "#151C2B",
        "text": "#F1F5F9",
        "muted": "#A3AFC4",
        "line": "#2A3550",
        "soft": "#1C2538",
        "softblue": "#1B2745",
        "input": "#1C2538",
        "track": "#2A3550",
        "shadow": "0 8px 30px rgba(0, 0, 0, 0.40)",
        "primary": "#5B93FF",
        "primarydark": "#8FB4FF",
        "stageicon": "#232D42",
        "stageiconfg": "#8391AB",
        "donebg": "#123524",
        "donefg": "#4ADE80",
    },
}

palette = PALETTES["dark" if DARK else "light"]

ROOT_VARS = (
    "<style>:root{"
    + ";".join(f"--{k}:{v}" for k, v in palette.items())
    + "}</style>"
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea {
    font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif !important;
}

/* ---------- page background ---------- */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--bg) !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stAppDeployButton"], [data-testid="stDeployButton"], .stDeployButton {
    display: none !important;
}
.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1500px;
}

/* ---------- text colors (theme-controlled) ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: var(--text) !important;
}
.stApp p, .stApp li, .stApp label, .stApp strong, .stApp em,
[data-testid="stWidgetLabel"] *, [data-testid="stText"], [data-testid="stText"] * {
    color: var(--text) !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: var(--muted) !important;
}
.stApp a, .stApp a * { color: var(--primary) !important; }
.stApp hr { border-color: var(--line) !important; }
.stApp code { background: var(--soft) !important; color: var(--text) !important; }

/* ---------- top bar ---------- */
.topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.brand-logo {
    width: 42px;
    height: 42px;
    object-fit: contain;
    border-radius: 10px;
}
.brand-name {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.3px;
}
.top-right { display: flex; align-items: center; gap: 12px; }
.chip {
    background: var(--card); border-radius: 999px; padding: 8px 14px;
    box-shadow: var(--shadow); font-size: 13px; color: var(--muted); font-weight: 500;
}
.user-chip {
    display: flex; align-items: center; gap: 10px; background: var(--card);
    border-radius: 999px; padding: 6px 16px 6px 6px; box-shadow: var(--shadow);
}
.avatar {
    width: 34px; height: 34px; border-radius: 50%;
    background: linear-gradient(135deg, #5B8DFF, #7C5CFF);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700;
}
.user-name { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.1; }
.user-sub { font-size: 11px; color: var(--muted); }

/* ---------- greeting ---------- */
.greeting h1 {
    font-size: 40px; font-weight: 700; margin: 4px 0 0 0; padding: 0;
    letter-spacing: -1px; line-height: 1.1; color: var(--text) !important;
}
.greeting p {
    font-size: 34px; font-weight: 300; margin: 0 0 18px 0;
    letter-spacing: -0.8px; line-height: 1.15; color: var(--text) !important;
}

/* ---------- stage chips ---------- */
.stages { display: flex; gap: 12px; flex-wrap: wrap; margin: 4px 0 6px 0; }
.stage {
    flex: 1 1 130px; background: var(--card); border-radius: 18px;
    padding: 14px 16px; box-shadow: var(--shadow);
    display: flex; align-items: center; gap: 12px;
}
.stage-icon {
    width: 36px; height: 36px; border-radius: 12px; display: flex;
    align-items: center; justify-content: center; font-size: 16px;
    background: var(--stageicon); color: var(--stageiconfg);
}
.stage.done .stage-icon { background: var(--donebg); color: var(--donefg); }
.stage-label { font-size: 12px; color: var(--muted); font-weight: 500; }
.stage-value { font-size: 14px; color: var(--text); font-weight: 700; }

/* ---------- pill navigation (main tabs) ---------- */
[data-baseweb="tab-list"] {
    background: var(--card) !important; border-radius: 999px; padding: 6px; gap: 4px;
    box-shadow: var(--shadow); width: fit-content; max-width: 100%;
}
button[role="tab"] {
    border-radius: 999px !important; padding: 8px 18px; height: auto;
    background: transparent !important;
}
button[role="tab"] p, button[role="tab"] div {
    color: var(--text) !important; font-weight: 600; font-size: 14px;
}
button[role="tab"][aria-selected="true"] { background: var(--primary) !important; }
button[role="tab"][aria-selected="true"] p,
button[role="tab"][aria-selected="true"] div { color: #FFFFFF !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* main tab panel = solid card */
[data-baseweb="tab-panel"] {
    background: var(--card) !important; border-radius: 26px;
    padding: 26px 28px !important; box-shadow: var(--shadow); margin-top: 16px;
}

/* nested tabs (inside history expanders) = underline tabs */
[data-baseweb="tab-panel"] [data-baseweb="tab-list"] {
    background: transparent !important; box-shadow: none; border-radius: 0; padding: 0;
    border-bottom: 1px solid var(--line); width: 100%;
}
[data-baseweb="tab-panel"] button[role="tab"] {
    border-radius: 8px 8px 0 0 !important; padding: 6px 12px;
}
[data-baseweb="tab-panel"] button[role="tab"][aria-selected="true"] {
    background: transparent !important; border-bottom: 2px solid var(--primary);
}
[data-baseweb="tab-panel"] button[role="tab"][aria-selected="true"] p,
[data-baseweb="tab-panel"] button[role="tab"][aria-selected="true"] div {
    color: var(--primary) !important;
}
[data-baseweb="tab-panel"] [data-baseweb="tab-panel"] {
    background: transparent !important; box-shadow: none; padding: 14px 0 0 0 !important;
    margin-top: 0; border-radius: 0;
}

/* ---------- headings ---------- */
[data-baseweb="tab-panel"] h2 { font-size: 1.35rem !important; font-weight: 700 !important; letter-spacing: -0.4px; }
[data-baseweb="tab-panel"] h3 { font-size: 1.1rem !important; font-weight: 700 !important; }

/* ---------- buttons ---------- */
.stApp .stButton > button, .stApp .stDownloadButton > button,
.stApp [data-testid="stFormSubmitButton"] > button,
.stApp [data-testid="stBaseButton-secondary"],
.stApp [data-testid="stBaseButton-secondaryFormSubmit"] {
    border-radius: 999px !important; padding: 8px 22px; font-weight: 600;
    border: 1px solid var(--line) !important; background: var(--card) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, .08); transition: all .15s ease;
}
.stApp .stButton > button p, .stApp .stDownloadButton > button p,
.stApp [data-testid="stFormSubmitButton"] > button p,
.stApp [data-testid="stBaseButton-secondary"] p,
.stApp [data-testid="stBaseButton-secondaryFormSubmit"] p {
    color: var(--text) !important;
}
.stApp .stButton > button:hover, .stApp .stDownloadButton > button:hover,
.stApp [data-testid="stFormSubmitButton"] > button:hover {
    border-color: var(--primary) !important;
}
.stApp .stButton > button[kind="primary"],
.stApp [data-testid="stBaseButton-primary"],
.stApp [data-testid="stBaseButton-primaryFormSubmit"],
.stApp [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #4F8CFF, #2F6BFF) !important;
    border: none !important; box-shadow: 0 8px 20px rgba(47, 107, 255, .30);
}
.stApp .stButton > button[kind="primary"] p,
.stApp [data-testid="stBaseButton-primary"] p,
.stApp [data-testid="stBaseButton-primaryFormSubmit"] p,
.stApp [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] p {
    color: #FFFFFF !important;
}
.stApp .stButton > button:disabled { opacity: .45; box-shadow: none; }

/* ---------- inputs ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div {
    background: var(--input) !important; border-color: var(--line) !important;
    border-radius: 14px !important;
}
.stApp input, .stApp textarea {
    color: var(--text) !important; -webkit-text-fill-color: var(--text) !important;
    background: transparent !important;
}
.stApp input::placeholder, .stApp textarea::placeholder {
    color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important;
}
[data-baseweb="select"] *, [data-baseweb="select"] input { color: var(--text) !important; }
[data-baseweb="select"] svg { fill: var(--muted) !important; }

/* dropdown menus (rendered in a popover) */
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"] {
    background: var(--card) !important; border: 1px solid var(--line);
    border-radius: 14px !important;
}
[data-baseweb="popover"] li, [data-baseweb="menu"] li, [role="option"] {
    background: var(--card) !important;
}
[data-baseweb="popover"] li *, [data-baseweb="menu"] li *, [role="option"] * {
    color: var(--text) !important;
}
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover, [role="option"]:hover {
    background: var(--soft) !important;
}

/* file uploader */
[data-testid="stFileUploader"] section {
    background: var(--softblue) !important; border: 1.5px dashed var(--primary) !important;
    border-radius: 18px !important;
}
[data-testid="stFileUploader"] * { color: var(--text) !important; }
[data-testid="stFileUploader"] small { color: var(--muted) !important; }

/* ---------- alerts, metrics, expanders ---------- */
[data-testid="stAlert"] {
    background: var(--soft) !important; border: 1px solid var(--line) !important;
    border-radius: 14px !important;
}
[data-testid="stAlertContainer"] { background: var(--soft) !important; }
[data-testid="stAlert"] * { color: var(--text) !important; }

[data-testid="stMetric"] { background: var(--softblue) !important; border-radius: 16px; padding: 14px 16px; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color: var(--text) !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: var(--muted) !important; }

[data-testid="stExpander"] { background: transparent !important; border: none !important; }
[data-testid="stExpander"] details {
    background: var(--card) !important; border: 1px solid var(--line) !important;
    border-radius: 18px !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
    color: var(--text) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line) !important; border-radius: 18px !important; }

/* ---------- symptoms table ---------- */
.tbl-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 16px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 14px; }
.tbl th {
    background: var(--soft) !important; color: var(--muted) !important; text-align: left;
    padding: 10px 14px; font-weight: 700; font-size: 11px;
    text-transform: uppercase; letter-spacing: .5px; border: none !important;
}
.tbl td {
    padding: 11px 14px; border: none !important; border-top: 1px solid var(--line) !important;
    color: var(--text) !important; background: transparent !important; vertical-align: top;
}

/* ---------- right rail cards ---------- */
.card {
    background: var(--card); border-radius: 24px; padding: 20px 22px;
    box-shadow: var(--shadow); margin-bottom: 16px;
}
.card-title { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 12px; }
.card-sub { font-size: 12px; color: var(--muted); }

.progress-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.progress-big { font-size: 28px; font-weight: 700; color: var(--text); letter-spacing: -1px; }
.progress-label { font-size: 13px; color: var(--muted); }
.track { background: var(--track); border-radius: 10px; height: 26px; overflow: hidden; }
.fill { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #BEF264, #4ADE80); }
.scale { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-top: 6px; }

.card-blue {
    background: linear-gradient(160deg, #5B93FF 0%, #2F6BFF 100%);
    box-shadow: 0 14px 34px rgba(47, 107, 255, .35);
}
.card-blue .card-title { color: #FFFFFF; margin-bottom: 2px; }
.card-blue .card-sub { color: rgba(255, 255, 255, .85); margin-bottom: 14px; }
.bars { display: flex; align-items: flex-end; gap: 5px; height: 92px; }
.bar { flex: 1; background: rgba(255, 255, 255, .92); border-radius: 4px; min-height: 5px; }
.bar.zero { background: rgba(255, 255, 255, .35); }
.blue-foot {
    margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, .25);
    font-size: 13px; font-weight: 600; display: flex; justify-content: space-between; color: #FFFFFF;
}

.profile { display: flex; gap: 14px; align-items: center; margin-bottom: 14px; }
.profile-avatar {
    width: 62px; height: 62px; border-radius: 50%;
    background: linear-gradient(135deg, #5B8DFF, #7C5CFF); color: #fff;
    display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700;
}
.profile-name { font-size: 16px; font-weight: 700; color: var(--text); }
.profile-meta { font-size: 12px; color: var(--muted); }
.mini-row {
    display: flex; justify-content: space-between; align-items: center;
    background: var(--soft); border-radius: 14px; padding: 10px 14px; margin-top: 8px;
}
.mini-label { font-size: 12px; color: var(--muted); }
.mini-value { font-size: 13px; font-weight: 700; color: var(--text); }
.pill { display: inline-block; border-radius: 999px; padding: 3px 10px; font-size: 11px; font-weight: 700; }

.reminder { display: flex; align-items: center; gap: 14px; }
.reminder-bar { width: 5px; align-self: stretch; border-radius: 5px; background: linear-gradient(180deg, #4ADE80, #2F6BFF); }
.reminder-title { font-size: 14px; font-weight: 700; color: var(--text); }
.reminder-text { font-size: 12px; color: var(--muted); margin-top: 2px; }

.week { display: flex; justify-content: space-between; gap: 6px; margin-bottom: 14px; }
.day {
    flex: 1; text-align: center; border-radius: 16px; padding: 10px 0 8px 0;
    font-size: 13px; color: var(--text); font-weight: 600;
}
.day small { display: block; font-size: 11px; color: var(--muted); font-weight: 500; margin-top: 2px; }
.day.today { background: #2F6BFF; color: #fff; box-shadow: 0 8px 18px rgba(47, 107, 255, .35); }
.day.today small { color: rgba(255, 255, 255, .88); }
.day .dot { display: block; margin: 4px auto 0 auto; width: 5px; height: 5px; border-radius: 50%; background: #4ADE80; }
.day.today .dot { background: #fff; }
.day .nodot { display: block; height: 9px; }

.visit { display: flex; align-items: center; gap: 12px; background: var(--soft); border-radius: 16px; padding: 10px 14px; margin-top: 8px; }
.visit-avatar {
    width: 36px; height: 36px; border-radius: 50%; background: var(--softblue); color: var(--primary);
    display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700;
}
.visit-info { flex: 1; min-width: 0; }
.visit-name { font-size: 13px; font-weight: 700; color: var(--text); }
.visit-date { font-size: 11px; color: var(--muted); }
.empty-note { font-size: 13px; color: var(--muted); }
</style>
"""

st.markdown(ROOT_VARS + CSS, unsafe_allow_html=True)


# ==========================================
# 3. HELPERS
# ==========================================

REVIEW_OPTIONS = ["Pending", "Reviewed", "Needs Correction"]

STATUS_ICON = {
    "Pending": "🟡",
    "Reviewed": "🟢",
    "Needs Correction": "🔴",
}

STATUS_COLORS_LIGHT = {
    "Pending": ("#FEF3C7", "#B45309"),
    "Reviewed": ("#DCFCE7", "#15803D"),
    "Needs Correction": ("#FEE2E2", "#B91C1C"),
}

STATUS_COLORS_DARK = {
    "Pending": ("#3B2F0B", "#FBBF24"),
    "Reviewed": ("#123524", "#4ADE80"),
    "Needs Correction": ("#3B1414", "#F87171"),
}

STATUS_COLORS = STATUS_COLORS_DARK if DARK else STATUS_COLORS_LIGHT
# ----------------------------------------------------------------------------------

@st.cache_resource
def load_whisper_model():

    return whisper.load_model("tiny")


def esc(value):

    return html_lib.escape(str(value))


def initials(name):

    parts = (name or "").split()

    if not parts:
        return "?"

    if len(parts) == 1:
        return parts[0][0].upper()

    return (parts[0][0] + parts[-1][0]).upper()


def status_pill(status):

    bg, fg = STATUS_COLORS.get(status, ("#E5E7EB", "#374151"))

    return (
        f'<span class="pill" style="background:{bg};color:{fg}">'
        f'{esc(status)}</span>'
    )


def parse_date(value):

    try:

        ts = pd.to_datetime(value, errors="coerce")

        if pd.isna(ts):
            return pd.NaT

        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.tz_localize(None)

        return ts

    except Exception:

        return pd.NaT


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
# 4. TOP BAR + GREETING
# ==========================================

# Load application logo
logo_path = Path("assets/logo.png")

with open(logo_path, "rb") as logo_file:
    logo_base64 = base64.b64encode(
        logo_file.read()
    ).decode()

today_label = datetime.now().strftime("%A, %d %b %Y")

st.markdown(
    '<div class="topbar">'
    '<div class="brand">'
    f'<img class="brand-logo" src="data:image/png;base64,{logo_base64}">'
    '<div class="brand-name">MedhāJīva</div></div>'
    '<div class="top-right">'
    f'<div class="chip">📅 {esc(today_label)}</div>'
    '<div class="user-chip"><div class="avatar">DR</div>'
    '<div><div class="user-name">Clinician</div>'
    '<div class="user-sub">AI Clinical Assistant</div></div></div>'
    '</div></div>',
    unsafe_allow_html=True
)

_, toggle_col = st.columns([5, 1])

with toggle_col:

    st.toggle("🌙 Dark mode", key="dark_mode")

st.markdown(
    '<div class="greeting">'
    '<h1>Hello Doctor!</h1>'
    "<p>Let's document today's consultation</p>"
    '</div>',
    unsafe_allow_html=True
)


# ==========================================
# 5. PAGE LAYOUT: MAIN AREA + RIGHT RAIL
# ==========================================

main_col, rail_col = st.columns([2.15, 1], gap="large")

rail_patient = None

with main_col:

    # Filled in at the end of the run so it reflects
    # the latest state after any button click.
    stages_slot = st.container()

    (
        tab_transcript,
        tab_soap,
        tab_symptoms,
        tab_cds,
        tab_save,
        tab_history
    ) = st.tabs([
        "🎙️ Transcript",
        "📝 SOAP",
        "🔍 Symptoms",
        "🧠 Insights",
        "💾 Save",
        "🗂️ History"
    ])

    # ------------------------------------------
    # TAB 1: AUDIO + TRANSCRIPT
    # ------------------------------------------

    with tab_transcript:

    
        st.header("Audio Input")

        audio_mode = st.radio(
            "Choose how you want to provide audio:",
            ["Record Consultation", "Upload Recording"],
            horizontal=True
        )

        uploaded_file = None

        if audio_mode == "Record Consultation":

            st.write("Record the doctor-patient conversation.")

            uploaded_file = st.audio_input(
                "Start recording",
                sample_rate=16000,
                key="consultation_recorder"
            )

            if uploaded_file is not None:
                st.success("Recording completed!")
                st.audio(uploaded_file)

        else:

            uploaded_file = st.file_uploader(
                "Upload consultation recording",
                type=["wav", "mp3", "m4a", "mpeg", "mpga", "webm"]
            )

            if uploaded_file is not None:
                st.success("Audio uploaded successfully!")
                st.audio(uploaded_file)


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

            b1, b2, _ = st.columns([1, 1.2, 2])

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

                table_html = (
                    '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
                    '<th>Symptom</th><th>Status</th><th>Duration</th>'
                    '<th>Severity</th><th>Evidence</th></tr></thead><tbody>'
                )

                for row in rows:

                    table_html += (
                        '<tr>'
                        f'<td><b>{esc(row["Symptom"])}</b></td>'
                        f'<td>{esc(row["Status"])}</td>'
                        f'<td>{esc(row["Duration"])}</td>'
                        f'<td>{esc(row["Severity"])}</td>'
                        f'<td>{esc(row["Evidence"])}</td>'
                        '</tr>'
                    )

                table_html += '</tbody></table></div>'

                st.markdown(table_html, unsafe_allow_html=True)

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

            save_patients = get_all_patients()

            patient_options = ["Register New Patient"]

            if save_patients:
                patient_options.append("Select Existing Patient")

            patient_mode = st.radio(
                "Patient Record",
                patient_options,
                horizontal=True,
                key="patient_mode"
            )

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
                            p["patient_id"] for p in save_patients
                        ],
                        format_func=lambda pid: next(
                            f'{p["name"] or "Unnamed Patient"} '
                            f'(ID: {p["patient_id"]})'
                            for p in save_patients
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

                rail_patient = selected_patient

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
# 6. DASHBOARD DATA (after all actions ran,
#    so every card shows the latest state)
# ==========================================

all_patients = get_all_patients()

entries = []

for p in all_patients:

    for r in get_patient_consultations(p["patient_id"]):

        entries.append({
            "pid": p["patient_id"],
            "name": p["name"] or "Unnamed Patient",
            "status": r["review_status"],
            "raw_date": r["consultation_date"],
            "ts": parse_date(r["consultation_date"]),
        })

today = pd.Timestamp.now().normalize()

counts_by_day = {}

for e in entries:

    if not pd.isna(e["ts"]):

        day_key = e["ts"].normalize().date()
        counts_by_day[day_key] = counts_by_day.get(day_key, 0) + 1

pending_count = sum(1 for e in entries if e["status"] == "Pending")


# ==========================================
# 7. WORKFLOW STAGE CHIPS (above the tabs)
# ==========================================

stage_defs = [
    ("🎙️", "Transcript", bool(current_transcript())),
    ("📝", "SOAP Notes", soap_is_current()),
    ("🔍", "Symptoms", symptoms_are_current()),
    ("🧠", "Insights", clinical_is_current()),
    ("💾", "Saved", bool(st.session_state.saved_consultation_id)),
]

stage_html = '<div class="stages">'

for icon_text, label, done in stage_defs:

    stage_html += (
        f'<div class="stage {"done" if done else ""}">'
        f'<div class="stage-icon">{"✓" if done else icon_text}</div>'
        f'<div><div class="stage-label">{esc(label)}</div>'
        f'<div class="stage-value">{"Done" if done else "Pending"}</div></div>'
        '</div>'
    )

stage_html += '</div>'

with stages_slot:

    st.markdown(stage_html, unsafe_allow_html=True)


# ==========================================
# 8. RIGHT RAIL CARDS
# ==========================================

done_count = sum(1 for _, _, done in stage_defs if done)
progress_pct = int(done_count / len(stage_defs) * 100)

if progress_pct == 0:
    progress_label = "Not started"
elif progress_pct < 100:
    progress_label = "In progress"
else:
    progress_label = "Complete"

progress_card = (
    '<div class="card">'
    '<div class="card-title">Workflow Progress</div>'
    f'<div class="progress-row"><span class="progress-big">{progress_pct}%</span>'
    f'<span class="progress-label">{progress_label}</span></div>'
    f'<div class="track"><div class="fill" style="width:{progress_pct}%"></div></div>'
    '<div class="scale"><span>0</span><span>100%</span></div>'
    '</div>'
)

# Clinic overview: consultations per day, last 14 days

bar_counts = []

for i in range(13, -1, -1):

    day_key = (today - pd.Timedelta(days=i)).date()
    bar_counts.append(counts_by_day.get(day_key, 0))

max_bar = max(bar_counts) if max(bar_counts) > 0 else 1

bars_html = ""

for c in bar_counts:

    if c == 0:
        bars_html += '<div class="bar zero" style="height:6%"></div>'
    else:
        height = 18 + int(82 * c / max_bar)
        bars_html += f'<div class="bar" style="height:{height}%"></div>'

overview_card = (
    '<div class="card card-blue">'
    '<div class="card-title">Clinic Overview</div>'
    '<div class="card-sub">Consultations saved, last 14 days</div>'
    f'<div class="bars">{bars_html}</div>'
    '<div class="blue-foot">'
    f'<span>{len(entries)} consultations</span>'
    f'<span>{len(all_patients)} patients</span>'
    '</div></div>'
)

# Patient profile

if rail_patient is not None:

    patient_entries = [
        e for e in entries if e["pid"] == rail_patient["patient_id"]
    ]

    last_entry = None

    if patient_entries:

        last_entry = max(
            patient_entries,
            key=lambda e: e["ts"] if not pd.isna(e["ts"]) else pd.Timestamp.min
        )

    rp_name = rail_patient["name"] or "Unnamed Patient"

    rp_age = (
        f'{rail_patient["age"]} years old'
        if rail_patient["age"] is not None
        else "Age not provided"
    )

    last_visit = esc(last_entry["raw_date"]) if last_entry else "No visits yet"

    last_status = status_pill(last_entry["status"]) if last_entry else "—"

    profile_card = (
        '<div class="card">'
        '<div class="card-title">Patient Profile</div>'
        '<div class="profile">'
        f'<div class="profile-avatar">{esc(initials(rp_name))}</div>'
        '<div>'
        f'<div class="profile-name">{esc(rp_name)}</div>'
        f'<div class="profile-meta">{esc(rp_age)} · ID {esc(rail_patient["patient_id"])}</div>'
        '</div></div>'
        '<div class="mini-row"><span class="mini-label">Consultations</span>'
        f'<span class="mini-value">{len(patient_entries)}</span></div>'
        '<div class="mini-row"><span class="mini-label">Last visit</span>'
        f'<span class="mini-value">{last_visit}</span></div>'
        '<div class="mini-row"><span class="mini-label">Last review</span>'
        f'<span>{last_status}</span></div>'
        '</div>'
    )

else:

    profile_card = (
        '<div class="card">'
        '<div class="card-title">Patient Profile</div>'
        '<div class="empty-note">Select a patient in the History tab '
        'to see their summary here.</div>'
        '</div>'
    )

# Review reminder

if pending_count:

    reminder_text = (
        f"{pending_count} consultation(s) awaiting clinician review."
    )

else:

    reminder_text = "No consultations are waiting for review."

reminder_card = (
    '<div class="card"><div class="reminder">'
    '<div class="reminder-bar"></div>'
    '<div><div class="reminder-title">Review Reminder</div>'
    f'<div class="reminder-text">{esc(reminder_text)}</div></div>'
    '</div></div>'
)

# Week strip + recent consultations

week_start = today - pd.Timedelta(days=today.weekday())

week_html = '<div class="week">'

for i in range(7):

    d = week_start + pd.Timedelta(days=i)

    is_today = d == today

    has_visits = counts_by_day.get(d.date(), 0) > 0

    marker = '<span class="dot"></span>' if has_visits else '<span class="nodot"></span>'

    week_html += (
        f'<div class="day {"today" if is_today else ""}">'
        f'{d.day}<small>{d.strftime("%a")}</small>{marker}</div>'
    )

week_html += '</div>'

recent = sorted(
    entries,
    key=lambda e: e["ts"] if not pd.isna(e["ts"]) else pd.Timestamp.min,
    reverse=True
)[:3]

if recent:

    visits_html = ""

    for e in recent:

        visits_html += (
            '<div class="visit">'
            f'<div class="visit-avatar">{esc(initials(e["name"]))}</div>'
            '<div class="visit-info">'
            f'<div class="visit-name">{esc(e["name"])}</div>'
            f'<div class="visit-date">{esc(e["raw_date"])}</div></div>'
            f'{status_pill(e["status"])}'
            '</div>'
        )

else:

    visits_html = '<div class="empty-note">No consultations saved yet.</div>'

recent_card = (
    '<div class="card">'
    '<div class="card-title">This Week</div>'
    f'{week_html}'
    '<div class="card-sub" style="margin-bottom:2px">Recent consultations</div>'
    f'{visits_html}'
    '</div>'
)

with rail_col:

    st.markdown(progress_card, unsafe_allow_html=True)
    st.markdown(overview_card, unsafe_allow_html=True)
    st.markdown(profile_card, unsafe_allow_html=True)
    st.markdown(reminder_card, unsafe_allow_html=True)
    st.markdown(recent_card, unsafe_allow_html=True)


# ==========================================
# 9. FOOTER
# ==========================================

st.caption(
    "MedhāJīva | AI Clinical Assistant | "
    "Educational prototype — not for clinical diagnosis. | "
    "Made by Sujal Deshmukh."
)