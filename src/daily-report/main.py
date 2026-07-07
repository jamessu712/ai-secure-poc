import os
import json
import pandas as pd
from jinja2 import Template
from openai import AzureOpenAI
from config import *
from datetime import datetime

# ==========================================
# 1. Configure Azure OpenAI credentials
# ==========================================
# AZURE_ENDPOINT = "https://your-azure-openai-resource.openai.azure.com/"
# AZURE_API_KEY = "your-azure-openai-api-key"
# AZURE_API_VERSION = "2024-02-15-preview"
# AZURE_DEPLOYMENT_NAME = "gpt-4o"  # Your Azure GPT-4o model deployment name

def analyze_and_generate_report(csv_path, template_path, output_path):
    print(f"Starting log file processing: {csv_path}...")

    # ==========================================
    # 2. Use Pandas to clean and aggregate Dynatrace data
    # ==========================================
    df = pd.read_csv(csv_path)

    # Calculate core KPI base numbers
    total_incidents = len(df)
    catalog_counts = df['Catalog'].value_counts().to_dict()
    sub_catalog_counts = df['Sub Catalog'].value_counts().to_dict()
    title_counts = df['Title'].value_counts().to_dict()

    # Safely get specific category metrics to avoid missing reports
    api_count = catalog_counts.get('API', 0)
    perf_count = catalog_counts.get('Performance', 0)
    api_percentage = round((api_count / total_incidents) * 100, 1) if total_incidents > 0 else 0

    # Extract top 6 detailed event list for HTML real-time log table display
    # Fill missing values and extract required fields
    df_filled = df.fillna({'Sub Catalog': 'N/A', 'Description': 'No description provided'})
    recent_incidents = df_filled[['Problem #', 'Title', 'Description', 'Issue Start Time', 'Duration (Minute)']].head(6).to_dict(orient='records')

    # Format time to only show hours and minutes for better front-end appearance
    for inc in recent_incidents:
        try:
            inc['Time_Short'] = inc['Issue Start Time'].split()[1][:5]
        except Exception:
            inc['Time_Short'] = "00:00"

    print("✅ Pandas data structuring completed.")

    # ==========================================
    # 3. Call Azure OpenAI to generate intelligent operations insights
    # ==========================================
    print("Requesting Azure OpenAI for LLM diagnostic summary...")
    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION
    )

    # Build business context prompt
    prompt = f"""
    You are a senior system operations expert responsible for an e-commerce platform. Based on the following error statistics captured by Dynatrace on 2026-05-28, write a 150–200 word Chinese "technical diagnostic insight" (Insight).
    Requirements: Professional and concise tone, directly point out the most critical system chain (e.g., which API chain), main failure types, and the core impact on the system, for presentation on executive and operations dashboards.

    【Today's Quick Metrics】:
    - Total incidents: {total_incidents}
    - Incident category distribution: {json.dumps(catalog_counts, ensure_ascii=False)}
    - Subsystem distribution: {json.dumps(sub_catalog_counts, ensure_ascii=False)}
    - Alert trigger type distribution: {json.dumps(title_counts, ensure_ascii=False)}
    """

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a senior operations expert who only speaks technical truth and cuts to the heart of the issue."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        ai_insight = response.choices[0].message.content.strip()
        print("✅ Azure OpenAI insight generated successfully.")
    except Exception as e:
        print(f"❌ Azure OpenAI call failed, using default text. Error: {e}")
        ai_insight = "Unable to load Azure AI real-time diagnostic insights. Please check network connection and Azure OpenAI credentials."

    # ==========================================
    # 4. Use Jinja2 template engine to inject data and generate HTML
    # ==========================================
    print("Rendering HTML dashboard page...")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    template = Template(template_content)

    # Pass all Python variables, dictionaries, and lists into the HTML template
    rendered_html = template.render(
        total_incidents=total_incidents,
        api_count=api_count,
        perf_count=perf_count,
        api_percentage=api_percentage,
        catalog_counts=catalog_counts,
        sub_catalog_counts=sub_catalog_counts,
        recent_incidents=recent_incidents,
        ai_insight=ai_insight
    )

    # Write the final report file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"🎉 Congratulations! The complete visualization dashboard has been successfully generated at: {output_path}")

if __name__ == "__main__":
    # Execute the script (ensure the file "05282026(Dynatrace).csv" exists in the current directory)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analyze_and_generate_report(
        csv_path="05282026(Dynatrace).csv",
        template_path="template.html",
        output_path=f"rm_daily_monitor_dashboard-bobs_{timestamp}.html"
    )