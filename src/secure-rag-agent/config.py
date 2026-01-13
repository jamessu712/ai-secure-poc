# config.py
from dotenv import load_dotenv
import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

load_dotenv()

KV_URI = os.getenv("KV_URI", "your-keyvault-name")

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KV_URI, credential=credential)

# Retrieve secrets from Key Vault
OPENAI_API_KEY = client.get_secret("openai-api-key").value
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "OPENAI_ENDPOINT")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")

SEARCH_API_KEY = client.get_secret("search-api-key").value
SEARCH_SERVICE_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT", "SEARCH_SERVICE_ENDPOINT")
INDEX_NAME = os.getenv("INDEX_NAME", "INDEX_NAME")

COGNITIVE_SERVICES_KEY = client.get_secret("cognitive-services-key").value
COGNITIVE_SERVICES_ENDPOINT = os.getenv("COGNITIVE_SERVICES_ENDPOINT", "COGNITIVE_SERVICES_ENDPOINT")

API_VERSION = os.getenv("API_VERSION", "API_VERSION")
# HMAC Salt for deterministic user ID (optional)
HMAC_SALT = client.get_secret("bobs-poc-hmac-salt").value

###############################################################
print(f"OPENAI_API_KEY = {OPENAI_API_KEY}")
print(f"OPENAI_ENDPOINT = {OPENAI_ENDPOINT}")

print(f"SEARCH_API_KEY = {SEARCH_API_KEY}")
print(f"SEARCH_SERVICE_ENDPOINT = {SEARCH_SERVICE_ENDPOINT}")

print(f"COGNITIVE_SERVICES_KEY = {COGNITIVE_SERVICES_KEY}")
print(f"COGNITIVE_SERVICES_ENDPOINT = {COGNITIVE_SERVICES_ENDPOINT}")

print(f"HMAC_SALT = {HMAC_SALT}")