


https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs?source=recommendations&utm_source=chatgpt.com&tabs=python-secure%2Cdotnet-entra-id&pivots=programming-language-csharp
https://learn.microsoft.com/en-us/azure/azure-portal/azure-portal-dashboards-create-programmatically?utm_source=chatgpt.com




- Create a client app
  - https://portal.azure.com/#allservices
```
rm -r daily-report -f
git clone https://github.com/jamessu712/ai-secure-poc daily-report
cd daily-report/src/daily-report

python -m venv labenv
./labenv/bin/Activate.ps1
pip install -r requirements.txt openai

code .env

python main.py
python main1.py
```