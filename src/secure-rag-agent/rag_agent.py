# rag_agent.py
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from .config import (
    OPENAI_ENDPOINT,
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    SEARCH_SERVICE_ENDPOINT,
    SEARCH_API_KEY,
    INDEX_NAME
)

def retrieve_context(query: str, top_k: int = 3) -> list[str]:
    # 1. Generate embedding for user query
    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        api_version="2024-02-01",
        azure_endpoint=OPENAI_ENDPOINT
    )
    emb = client.embeddings.create(input=[query], model="text-embedding-ada-002").data[0].embedding

    # 2. Vector search (return only redacted content)
    search_client = SearchClient(
        endpoint=SEARCH_SERVICE_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )

    vector_query = VectorizedQuery(vector=emb, k_nearest=3, fields="embedding")
    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        select=["content"],
        top=top_k
    )

    return [doc["content"] for doc in results]

def generate_answer(user_question: str) -> str:
    context_list = retrieve_context(user_question)
    context = "\n".join(context_list)

    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        api_version="2024-02-01",
        azure_endpoint=OPENAI_ENDPOINT
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use only the provided context."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_question}"}
    ]

    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.3
    )
    return response.choices[0].message.content
