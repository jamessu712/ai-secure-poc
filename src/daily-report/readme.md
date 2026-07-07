



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
```