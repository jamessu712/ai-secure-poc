





- Create a Microsoft Foundry hub and project
    - https://ai.azure.com/managementCenter/allResources
   ```
   Resource Group : BobsRM
   Project Name : prj-bobs-poc
   Azure AI hub : hub-bobs-poc
   Azure AI Foundry Name : fdy-bobs-poc 
   Region : East US 2
   ```

- Deploy models (https://learn.microsoft.com/en-us/training/modules/explore-models-azure-ai-studio/)
  - embedding model - (text-embedding-ada-00)
   ```
   Deployment name: text-embedding-bobs-poc
   Deployment type: Global Standard
   Model version: 2 (Default)
   Connected AI resource: fdy-bobs-poc
   Tokens per Minute Rate Limit (thousands): 50K (or the maximum available in your subscription if less than 50K)
   Content filter: DefaultV2
   ```
  - chat model - (gpt-4o)
   ```
   Deployment name: chat-bobs-poc
   Deployment type: Global Standard
   Model version: 2 (Default)
   Connected AI resource: fdy-bobs-poc
   Tokens per Minute Rate Limit (thousands): 50K (or the maximum available in your subscription if less than 50K)
   Content filter: DefaultV2
   ```

- create service
  - Language
  ```
  name : Language-bobs-poc
  ```
  - AI Search
  ```
  name : search-bobs-poc
  ```
  
- Add data to your project



- Create an index for your data

   ```
   Subscription: You Azure subscription
   Resource group: BobsRM
   Service name: search-service-bobs-poc
   Location: West US
   Pricing tier: Basic
   ```


- Test the index in the playground

- Create a RAG client app
  - https://portal.azure.com/#allservices
    ```
    rm -r ai-secure-poc -f
    git clone https://github.com/jamessu712/ai-secure-poc ai-secure-poc
    ```

    ```
    cd ai-secure-poc/src/secure-rag-agent
    ```

    ```
    python -m venv labenv
    ./labenv/bin/Activate.ps1
    pip install -r requirements.txt openai
    ```

    ```
    code .env
    ```

    ```
    python main.py
    
    python -m secure-rag-agent.main
    ```
    

  
- Clean up
    - https://portal.azure.com