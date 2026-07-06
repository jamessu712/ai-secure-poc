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

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "AZURE_ENDPOINT")
OPENAI_API_KEY = client.get_secret("openai-api-key").value
API_VERSION = os.getenv("API_VERSION", "API_VERSION")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "AZURE_DEPLOYMENT_NAME")