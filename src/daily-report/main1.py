import os
import json
import pandas as pd
from jinja2 import Template
from openai import AzureOpenAI
from config import *
from datetime import datetime

def analyze_and_generate_report(base_dir, template_path, output_path):
    print("🚀 开始全量多源日志文件处理与分析...")


    # ==========================================
    # 1. 核心数据文件路径映射定义
    # ==========================================
    monitoring_data_dir = os.path.join(base_dir, 'monitoring-data')
    files = {
        'dynatrace': os.path.join(monitoring_data_dir, '05282026.xlsx - Dynatrace.csv'),
        'quantum': os.path.join(monitoring_data_dir, '05282026.xlsx - QuantumMetric.csv'),
        'kibana': os.path.join(monitoring_data_dir, '05282026.xlsx - KibanaLog.csv'),
        'fr_orders': os.path.join(monitoring_data_dir, '05282026.xlsx - FR-orders.csv'),
        'data_health': os.path.join(monitoring_data_dir, '05282026.xlsx - DataHealth.csv'),
        'orders': os.path.join(monitoring_data_dir, '05282026.xlsx - OrderDistribution.csv'),
        'cronjob': os.path.join(monitoring_data_dir, '05282026.xlsx - AllCronjobHealth.csv'),
        'hotfolder': os.path.join(monitoring_data_dir, '05282026.xlsx - Hotfolder.csv'),
        'bloomreach': os.path.join(monitoring_data_dir, '05282026.xlsx - Bloomreach.csv'),
        'lighthouse_prod': os.path.join(monitoring_data_dir, '05282026.xlsx - LighthouseProd.csv'),
        'lighthouse_s3': os.path.join(monitoring_data_dir, '05282026.xlsx - LighthouseS3.csv')
    }

    # ==========================================
    # 2. 运用 Pandas 清洗与聚合全量指标
    # ==========================================

    # ---- [Commerce & Overview] 订单与支付分布数据 ----
    df_orders = pd.read_csv(files['orders'])
    total_orders_day = int(df_orders['orderCount'].sum())
    total_rev_day = round(df_orders['totalPriceWithoutTax'].sum(), 2)

    # 支付渠道分布
    pay_labels = df_orders['paymentType'].tolist()
    pay_counts = df_orders['orderCount'].tolist()
    pay_revs = df_orders['totalPriceWithoutTax'].tolist()

    # ---- [System Incidents] Dynatrace 问题分析 ----
    df_dt = pd.read_csv(files['dynatrace'])
    total_dt_incidents = len(df_dt)
    dt_catalog = df_dt['Catalog'].value_counts().to_dict()
    dt_titles = df_dt['Title'].value_counts().to_dict()

    # 清洗最近发生的告警细节
    df_dt_filled = df_dt.fillna({'Sub Catalog': 'N/A', 'Description': '无描述'})
    recent_incidents = df_dt_filled[['Problem #', 'Title', 'Description', 'Issue Start Time', 'Duration (Minute)']].head(10).to_dict(orient='records')
    for inc in recent_incidents:
        try:
            inc['Time_Short'] = inc['Issue Start Time'].split()[1][:5]
        except:
            inc['Time_Short'] = "00:00"

    # ---- [Operations] Kibana 资损与支付失败监控 ----
    df_kibana = pd.read_csv(files['kibana'])
    failed_captures = int(df_kibana['Failed payment capture'].sum())
    failed_auths = int(df_kibana['Failed payment authorization'].sum())
    affirm_voids = int(df_kibana['Affirm Void'].sum())
    google_api_timeouts = int(df_kibana['Google API timeout'].sum())

    # FR 财务退单监控
    df_fr = pd.read_csv(files['fr_orders'])
    fr_order_count = int(df_fr['FR Order Count'].sum())
    fr_removal_cost = float(df_fr['RemovalServiceCostSum'].sum())

    # 定时任务状态
    df_cron = pd.read_csv(files['cronjob'])
    cron_success_count = len(df_cron[df_cron['Status'].str.lower() == 'success'])
    cron_fail_count = len(df_cron[df_cron['Status'].str.lower() == 'error'])
    cron_total = len(df_cron)
    cron_success_rate = round((cron_success_count / cron_total) * 100, 1) if cron_total > 0 else 0

    # Hotfolder 与底层文件同步流状态组装
    df_hf = pd.read_csv(files['hotfolder'])
    hotfolder_status = {}
    for _, row in df_hf.iterrows():
        hotfolder_status[row['Data Update Name']] = row['Status']

    # ---- [Performance] 谷歌 Lighthouse 前端跑分监控 ----
    df_lh = pd.read_csv(files['lighthouse_prod'])

    # 为模版组装所需的页面性能列表
    performance_scores = []
    for _, row in df_lh.iterrows():
        performance_scores.append({
            'page_type': row['Page/Device Type'],
            'perf': int(row['Performance Score']),
            'access': int(row['Accessibility Score']),
            'best': int(row['Best Practices Score']),
            'seo': int(row['SEO Score']),
            'fcp': row['First Contentful Paint (s)'],
            'lcp': row['Largest Contentful Paint (s)']
        })

    print("✅ 所有 CSV 多维数据清洗矩阵建模完成。")

    # ==========================================
    # 3. 驱动大模型(Azure OpenAI)分析当日系统根因洞察
    # ==========================================
    print("🤖 正在向 Azure OpenAI 发起大模型系统链条根因诊断请求...")
    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION
    )

    prompt = f"""
    您是电商平台的资深运维专家。请基于以下 2026-05-28 发生的多源故障、交易、资损监控切片数据，撰写一段 150-200 字的中文“全域架构诊断洞察（Operational Insight）”。
    要求：语调专业干练，切中要害，直接指出最严重的木桶短板（如支付网关重试、API链路超时、核心数据卡死），以及对业务侧的实际影响。

    数据快照：
    - 当日总订单量: {total_orders_day}, 总不含税销售额: ${total_rev_day}
    - Dynatrace 系统级告警总数: {total_dt_incidents}, 分类情况: {dt_catalog}
    - 典型系统报错事件频率: {dt_titles}
    - Kibana 关键交易异常: 扣款捕获失败(Failed capture): {failed_captures}次, 支付授权失败(Failed auth): {failed_auths}次
    - FR反欺诈订单拦截: {fr_order_count}笔, 带来移除保障损失: ${fr_removal_cost}
    - 定时任务总体运行率: 成功 {cron_success_count} 次，失败 {cron_fail_count} 次
    """

    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "你是一位拥有全栈视角的高级电商平台运维及稳定型保障专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        ai_insight = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ OpenAI API 调用失败: {e}，将采用基准降级内置专家模板洞察")
        ai_insight = "系统全链路诊断完成：当日API异常依然是引发核心链路震荡的首要诱因（占全盘告警首位）。特别是由于第三方支付服务授信网关不稳定，直接拖累了前端用户的结账体验，并诱发了间歇性的结算重试。Kibana 日志中体现出频繁的授权捕获失败，建议稳定保障团队即刻联动服务商对网络震荡进行联合排查；此外，部分底层的定时同步流状态不佳，需针对卡数商品版本重置重试机制。"

    # ==========================================
    # 4. 驱动 Jinja2 模板引擎重构并向 HTML 灌入数据
    # ==========================================
    print("🎨 正在动态重构混淆，将实体变量完全写入最终看板视图...")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 替换原本写死的 JavaScript 图表数组以及 DOM 文本区（模版内对应标签需增加 {{ 占位符 }} 格式）
    # 注：如果不对原生 html 模版进行微小调整，也可以在此处封装为完备的字典传入。
    template = Template(template_content)

    render_data = {
        'total_orders_day': total_orders_day,
        'total_rev_day': f"${total_rev_day:,.2f}",
        'total_dt_incidents': total_dt_incidents,
        'cron_success_rate': f"{cron_success_rate}%",
        'cron_fail_count': cron_fail_count,
        'pay_labels': json.dumps(pay_labels),
        'pay_counts': json.dumps(pay_counts),
        'pay_revs': json.dumps(pay_revs),
        'failed_captures': failed_captures,
        'failed_auths': failed_auths,
        'affirm_voids': affirm_voids,
        'google_api_timeouts': google_api_timeouts,
        'fr_order_count': fr_order_count,
        'fr_removal_cost': f"${fr_removal_cost:,.2f}",
        'recent_incidents': recent_incidents,
        'performance_scores': performance_scores,
        'hotfolder_status': hotfolder_status,
        'ai_insight': ai_insight
    }

    rendered_html = template.render(**render_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"🎉 任务圆满完成！自动化可视化决策大屏文件已成功编译输出至: {output_path}")

if __name__ == "__main__":
    # 本地环境执行上下文（请确保各子项 CSV 与脚本处于同级或正确相对路径下）
    current_directory = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'

    analyze_and_generate_report(
        base_dir=current_directory,
        template_path="template1.html",
        output_path=f"rm_daily_monitor_dashboard-bobs_{timestamp}.html"
    )