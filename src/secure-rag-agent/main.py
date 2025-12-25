# main.py
from pii_redactor import redact_pii
from pii_redactor import hash_email
from vector_store import upsert_document
from rag_agent import generate_answer
from rag_agent import rag_QA
from config import HMAC_SALT
import uuid

# === Simulate user behavior log ingestion ===
raw_logs = [
    "User alice@example.com viewed product laptop.",
    "john.doe@company.org added item to cart.",
    "Contact support at help@service.com for issues."
]

# Redact PII and store in database
# for log in raw_logs:
#     redacted = redact_pii(log, HMAC_SALT)
#     doc_id = str(uuid.uuid4())
#     print(f"doc_id = {doc_id}")
#     upsert_document(doc_id, log, redacted)  # Note: original log is not stored!

print("All logs ingested securely.")

# === RAG query example ===
# rag with unredacted
question = "What did user john.doe@company.org do?"
rag_QA(question)

# rag with hashed email
hashed = hash_email("john.doe@company.org", HMAC_SALT)
placeholder = f"user_{hashed}"
question = f"What did user {placeholder} do?"
rag_QA(question)

# rag with redacted
question = "What did user user_c286a3aeca0af2f3 do?"
rag_QA(question)

