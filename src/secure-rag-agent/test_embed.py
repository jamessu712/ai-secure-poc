from openai import AzureOpenAI

client = AzureOpenAI(
    api_key="YOUR_API_KEY",
    api_version="2023-05-15",
    azure_endpoint="https://YOUR_RESOURCE.openai.azure.com/"
)

try:
    resp = client.embeddings.create(
        input=["Hello world"],
        model="YOUR_EMBED_DEPLOYMENT_NAME"
    )
    print("Success! Dim:", len(resp.data[0].embedding))
except Exception as e:
    print("Error:", e)