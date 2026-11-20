import sqlite3
import json

from pathlib import Path
from datetime import datetime


# ==========================================
# 1. DATABASE LOCATION
# ==========================================

DB_PATH = Path(__file__).parent / "medhajiva.db"


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# 3. CREATE DATABASE TABLES
# ==========================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # Patient table

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (

            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            age INTEGER,

            created_at TEXT NOT NULL

        )
    """)

    # Consultation table

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultations (

            consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_id INTEGER NOT NULL,

            consultation_date TEXT NOT NULL,

            transcript TEXT NOT NULL,

            soap_notes TEXT,

            symptoms TEXT,

            clinical_results TEXT,

            review_status TEXT NOT NULL DEFAULT 'Pending',

            FOREIGN KEY (patient_id)
            REFERENCES patients(patient_id)

        )
    """)

    connection.commit()

    connection.close()


# ==========================================
# 4. ADD A PATIENT
# ==========================================

def add_patient(name=None, age=None):

    if age is not None and not 0 <= age <= 120:
        raise ValueError("Age must be between 0 and 120.")

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO patients (name, age, created_at)

        VALUES (?, ?, ?)
    """, (
        name,
        age,
        datetime.now().astimezone().isoformat(timespec="seconds")
    ))

    patient_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return patient_id


# ==========================================
# 5. SAVE CONSULTATION
# ==========================================

def save_consultation(
    patient_id,
    transcript,
    soap_notes=None,
    symptoms=None,
    clinical_results=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO consultations (

            patient_id,
            consultation_date,
            transcript,
            soap_notes,
            symptoms,
            clinical_results,
            review_status

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (

        patient_id,

        datetime.now().astimezone().isoformat(timespec="seconds"),

        transcript,

        json.dumps(soap_notes, ensure_ascii=False)
        if soap_notes is not None else None,

        json.dumps(symptoms, ensure_ascii=False)
        if symptoms is not None else None,

        json.dumps(clinical_results, ensure_ascii=False)
        if clinical_results is not None else None,

        "Pending"

    ))

    consultation_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return consultation_id


# ==========================================
# 6. GET PATIENT CONSULTATIONS
# ==========================================

def get_patient_consultations(patient_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM consultations
        WHERE patient_id = ?
        ORDER BY consultation_date DESC
    """, (patient_id,))

    records = cursor.fetchall()

    connection.close()

    results = []

    for record in records:

        item = dict(record)

        # Convert stored JSON strings back to Python objects

        for field in [
            "soap_notes",
            "symptoms",
            "clinical_results"
        ]:

            if item[field] is not None:

                item[field] = json.loads(item[field])

        results.append(item)

    return results


# ==========================================
# 7. GET ALL PATIENTS
# ==========================================

def get_all_patients():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT patient_id, name, age
        FROM patients
        ORDER BY patient_id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return [dict(record) for record in records]


# ==========================================
# 8. UPDATE CONSULTATION REVIEW STATUS
# ==========================================

def update_review_status(consultation_id, status):

    allowed_statuses = [
        "Pending",
        "Reviewed",
        "Needs Correction"
    ]

    if status not in allowed_statuses:
        raise ValueError("Invalid review status.")

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE consultations
        SET review_status = ?
        WHERE consultation_id = ?
    """, (status, consultation_id))

    connection.commit()

    updated_rows = cursor.rowcount

    connection.close()

    return updated_rows
