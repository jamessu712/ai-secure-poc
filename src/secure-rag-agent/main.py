# main.py
from pii_redactor import redact_pii
from vector_store import upsert_document
from rag_agent import generate_answer
from config import HMAC_SALT
import uuid

# === Simulate user behavior log ingestion ===
raw_logs = [
    "User alice@example.com viewed product laptop.",
    "john.doe@company.org added item to cart.",
    "Contact support at help@service.com for issues."
]

# Redact PII and store in database
for log in raw_logs:
    redacted = redact_pii(log, HMAC_SALT)
    doc_id = str(uuid.uuid4())
    upsert_document(doc_id, log, redacted)  # Note: original log is not stored!

print("All logs ingested securely.")

# === RAG query example ===
question = "What did user user_a1b2c3d4e5f67890 view?"
answer = generate_answer(question)
print(f"Q: {question}")
print(f"A: {answer}")
