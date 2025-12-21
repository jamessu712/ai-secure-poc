# pii_redactor.py
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from .config import COGNITIVE_SERVICES_ENDPOINT, COGNITIVE_SERVICES_KEY
import hashlib
import hmac

def hash_email(email: str, salt: str) -> str:
    """Deterministic hash email for anonymization but traceable"""
    return hmac.new(salt.encode(), email.lower().encode(), hashlib.sha256).hexdigest()[:16]

def redact_pii(text: str, salt: str) -> str:
    """
    Use Azure Text Analytics to redact PII, and replace emails with hash_id
    """
    client = TextAnalyticsClient(
        endpoint=COGNITIVE_SERVICES_ENDPOINT,
        credential=AzureKeyCredential(COGNITIVE_SERVICES_KEY)
    )

    # Step 1: Identify PII
    response = client.recognize_pii_entities([text], language="en")
    result = response[0]

    if result.is_error:
        raise Exception(f"PII detection failed: {result.error}")

    # Step 2: Replace emails with hash_id, other PII with <REDACTED>
    redacted_text = text
    entities = sorted(result.entities, key=lambda e: e.offset, reverse=True)
    for entity in entities:
        if entity.category == "Email":
            hashed = hash_email(entity.text, salt)
            placeholder = f"user_{hashed}"
        else:
            placeholder = "<REDACTED>"
        start = entity.offset
        end = start + entity.length
        redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]

    return redacted_text
