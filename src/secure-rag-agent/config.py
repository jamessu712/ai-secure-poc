# config.py
import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

KEY_VAULT_NAME = os.getenv("KEY_VAULT_NAME", "your-keyvault-name")
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KV_URI, credential=credential)

# Retrieve secrets from Key Vault
OPENAI_API_KEY = client.get_secret("openai-api-key").value
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "OPENAI_ENDPOINT")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")

SEARCH_API_KEY = client.get_secret("search-api-key").value
SEARCH_SERVICE_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT", "SEARCH_SERVICE_ENDPOINT")
INDEX_NAME = "user-behavior-secure-index"

COGNITIVE_SERVICES_KEY = client.get_secret("cognitive-services-key").value
COGNITIVE_SERVICES_ENDPOINT = os.getenv("COGNITIVE_SERVICES_ENDPOINT", "COGNITIVE_SERVICES_ENDPOINT")

# HMAC Salt for deterministic user ID (optional)
HMAC_SALT = client.get_secret("hmac-salt").value
