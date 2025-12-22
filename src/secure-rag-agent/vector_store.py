# vector_store.py
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from config import (
    OPENAI_ENDPOINT,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    SEARCH_SERVICE_ENDPOINT,
    SEARCH_API_KEY,
    INDEX_NAME
)

def get_embedding(text: str) -> list[float]:
    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        api_version="2023-05-15",
        azure_endpoint=OPENAI_ENDPOINT
    )
    response = client.embeddings.create(input=[text], model=OPENAI_EMBEDDING_MODEL)
    return response.data[0].embedding

def upsert_document(doc_id: str, original_text: str, redacted_text: str):
    embedding = get_embedding(redacted_text)

    search_client = SearchClient(
        endpoint=SEARCH_SERVICE_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )

    doc = {
        "id": doc_id,
        "content": redacted_text,          # Redacted text
        "original_snippet": None,          # Do not store original text!
        "embedding": embedding
    }

    search_client.upload_documents(documents=[doc])
    print(f"Document {doc_id} indexed securely.")
