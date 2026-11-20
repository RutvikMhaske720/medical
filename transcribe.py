import whisper
import os

# ==============================
# 1. Load Whisper model
# ==============================

print("Loading Whisper model...")

model = whisper.load_model("tiny")

print("Model loaded successfully!")


# ==============================
# 2. Audio file path
# ==============================

audio_path = "audio/sample.wav.m4a"

# -------------------------------------
#   check were python is searching
# -------------------------------------

print("Current working directory:", os.getcwd())
print("Checking audio path:", os.path.abspath(audio_path))
print("File exists:", os.path.exists(audio_path))

# ==============================
# 3. Transcribe audio
# ==============================

if os.path.exists(audio_path):

    print("\nTranscribing audio...")

    result = model.transcribe(
        audio_path,
        fp16=False
    )

    transcript = result["text"]

    print("\n========== TRANSCRIPT ==========\n")

    print(transcript)


    # ==============================
    # 4. Save transcript
    # ==============================

    os.makedirs("output", exist_ok=True)

    with open("output/transcript.txt", "w", encoding="utf-8") as file:
        file.write(transcript)

    print("\nTranscript saved successfully!")

else:

    print("Audio file not found!")
