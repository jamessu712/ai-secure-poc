# main.py
from pii_redactor import redact_pii
from pii_redactor import hash_email
from pii_redactor import hash_pii
from vector_store import upsert_document
from rag_agent import generate_answer
from rag_agent import rag_QA
from config import HMAC_SALT
import uuid

# === Simulate user behavior log ingestion ===
# raw_logs = [
#     "User alice@example.com viewed product laptop.",
#     "john.doe@company.org added item to cart.",
#     "Contact support at help@service.com for issues."
# ]

raw_logs = [
    "james_81@gmail.com|User name is James Su|This user's goal was to purchase a sectional, but they struggled significantly during the checkout process. After initially adding a sectional to their cart, they encountered an \"Access is denied\" error during sign-in, which also caused their cart to be lost. They then added a different sectional to their cart, but faced another error when attempting to add it, and subsequently removed items from their cart before proceeding to payment. The user spent the majority of their time on the payment details page, where they ultimately attempted to apply for a \"Lease to Own\" payment option. ",
    "jimmy_91@yahoo.com|User name is Jimmy Wang|The user's goal was to purchase living room furniture, but they struggled significantly with the checkout process, specifically with payment and shipping details. They spent a considerable amount of time on the financing options page and encountered multiple API errors related to payment processing and account roles. The user was unable to complete the purchase.",
    "toby_21@hotmail.com|User name is Toby Smith|The user's goal was to purchase furniture, specifically a sofa table. They struggled significantly during the checkout process, encountering multiple API errors related to login and payment, which ultimately prevented them from completing their purchase. They spent a considerable amount of time on the payment details page, attempting to use a \"Lease to Own\" option."
]

# Redact PII and store in database
# for log in raw_logs:
#     redacted = redact_pii(log, HMAC_SALT)
#     doc_id = str(uuid.uuid4())
#     print(f"doc_id = {doc_id}")
#     upsert_document(doc_id, log, redacted)  # Note: original log is not stored!

# print("All logs ingested securely.")


# question = "What did user james su do?"
# rag_QA(question)

# question = "What did user James Su do?"
# rag_QA(question)

# question = "What did user james_81@gmail.com do?"
# rag_QA(question)

# question = "What did user user_34405f0d347eacdb do?"
# rag_QA(question)

# question = "What did user name_f4adebab7e2bd95e do?"
# rag_QA(question)


# rag with hashed email
# hashed = hash_pii("james_81@gmail.com", HMAC_SALT)
# placeholder = f"user_{hashed}"
# question = f"What did user {placeholder} do?"
# rag_QA(question)

# rag with hashed name
hashed = hash_pii("james su", HMAC_SALT)
placeholder = f"user_{hashed}"
question = f"What did user {placeholder} do?"
rag_QA(question)

hashed = hash_pii("James Su", HMAC_SALT)
placeholder = f"user_{hashed}"
question = f"What did user {placeholder} do?"
rag_QA(question)

