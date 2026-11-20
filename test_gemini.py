from soap_generator import generate_soap_notes


sample_transcript = """
Doctor: What problem are you experiencing?

Patient: I have had fever for three days.
I also have headache and body pain.

Doctor: Do you have a cough?

Patient: No, I don't have a cough.

Doctor: Okay. We will check your temperature
and consider further examination.
"""


print("Generating SOAP notes...")

soap = generate_soap_notes(sample_transcript)

if soap is None:
    print("SOAP generation failed. Please try again.")
    exit()

print("\n========== SOAP NOTES ==========")

print("\nSUBJECTIVE:")
print(soap["subjective"])

print("\nOBJECTIVE:")
print(soap["objective"])

print("\nASSESSMENT:")
print(soap["assessment"])

print("\nPLAN:")
print(soap["plan"])

print("\nMISSING INFORMATION:")
for item in soap["missing_information"]:
    print("-", item)
