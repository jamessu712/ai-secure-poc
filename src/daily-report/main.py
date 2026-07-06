import os
import json
import pandas as pd
from jinja2 import Template
from openai import AzureOpenAI

# ==========================================
# 1. 配置 Azure OpenAI 凭证
# ==========================================
# AZURE_ENDPOINT = "https://your-azure-openai-resource.openai.azure.com/"
# AZURE_API_KEY = "your-azure-openai-api-key"
# AZURE_API_VERSION = "2024-02-15-preview"
# AZURE_DEPLOYMENT_NAME = "gpt-4o"  # 您的 Azure GPT-4o 模型部署名称

def analyze_and_generate_report(csv_path, template_path, output_path):
    print(f"开始处理日志文件: {csv_path}...")
    
    # ==========================================
    # 2. 使用 Pandas 清洗和聚合 Dynatrace 数据
    # ==========================================
    df = pd.read_csv(csv_path)
    
    # 计算核心 KPI 基础数字
    total_incidents = len(df)
    catalog_counts = df['Catalog'].value_counts().to_dict()
    sub_catalog_counts = df['Sub Catalog'].value_counts().to_dict()
    title_counts = df['Title'].value_counts().to_dict()
    
    # 安全获取具体的分类指标，防止漏报
    api_count = catalog_counts.get('API', 0)
    perf_count = catalog_counts.get('Performance', 0)
    api_percentage = round((api_count / total_incidents) * 100, 1) if total_incidents > 0 else 0
    
    # 提取排名前 6 的详细事件列表用于 HTML 实时日志表格展示
    # 填充缺失值并提取所需字段
    df_filled = df.fillna({'Sub Catalog': 'N/A', 'Description': 'No description provided'})
    recent_incidents = df_filled[['Problem #', 'Title', 'Description', 'Issue Start Time', 'Duration (Minute)']].head(6).to_dict(orient='records')
    
    # 格式化时间，只保留时分显示，优化前端观感
    for inc in recent_incidents:
        try:
            inc['Time_Short'] = inc['Issue Start Time'].split()[1][:5]
        except Exception:
            inc['Time_Short'] = "00:00"

    print("✅ Pandas 数据结构化提取完成。")

    # ==========================================
    # 3. 调用 Azure OpenAI 生成智能运维见解
    # ==========================================
    print("正在请求 Azure OpenAI 生成大模型诊断总结...")
    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION
    )
    
    # 构造业务上下文 Prompt
    prompt = f"""
    你是一个负责电商平台的资深系统运维专家。请根据以下 2026-05-28 当天 Dynatrace 捕获的报错统计数据，写一段 150 到 200 字之间的中文“技术诊断见解”（Insight）。
    要求：语气专业、简练，直接指出最严重的系统链路（如哪种 API 链路）、主要故障类型以及对系统的核心影响，用于呈现在高管和运维大屏的看板上。
    
    【今日指标快报】：
    - 总突发事件数: {total_incidents} 起
    - 事件大类分布: {json.dumps(catalog_counts, ensure_ascii=False)}
    - 细分子系统分布: {json.dumps(sub_catalog_counts, ensure_ascii=False)}
    - 警报触发类型分布: {json.dumps(title_counts, ensure_ascii=False)}
    """
    
    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "你是一个只说技术大实话、直击问题要害的资深运维专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        ai_insight = response.choices[0].message.content.strip()
        print("✅ Azure OpenAI 智能见解生成成功。")
    except Exception as e:
        print(f"❌ Azure OpenAI 调用失败，将使用默认文本。错误信息: {e}")
        ai_insight = "无法加载 Azure AI 实时诊断见解。请检查网络连接及 Azure OpenAI 凭证状态。"

    # ==========================================
    # 4. 使用 Jinja2 模板引擎注入数据并生成 HTML
    # ==========================================
    print("开始渲染 HTML 看板页面...")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    template = Template(template_content)
    
    # 将所有 Python 变量、字典、列表传入 HTML 模板
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
    
    # 输出最终的报表文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
        
    print(f"🎉 恭喜！完整的可视化大屏报表已成功生成至: {output_path}")

if __name__ == "__main__":
    # 执行脚本（确保当前目录下有 05282026(Dynatrace).csv 文件）
    analyze_and_generate_report(
        csv_path="05282026(Dynatrace).csv",
        template_path="template.html",
        output_path="rm_daily_monitor_dashboard-bobs.html"
    )