import os
import json
import glob
import pandas as pd
from jinja2 import Template
from openai import AzureOpenAI
from config import *
from datetime import datetime
import re

def parse_date_from_filename(filename):
    """从文件名如 '05282026.xlsx' 解析出日期字符串 '2026-05-28'"""
    base = os.path.splitext(filename)[0]
    # 假设格式为 MMDDYYYY
    if len(base) == 8 and base.isdigit():
        month = base[:2]
        day = base[2:4]
        year = base[4:8]
        return f"{year}-{month}-{day}"
    else:
        return base  # fallback

def format_date_label(date_str):
    """将 '2026-05-28' 转为 '5/28' 或 '5/28/2026' 用于显示"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%m/%d/%Y")  # 例如 "05/28/2026"
    except:
        return date_str

def analyze_and_generate_report(data_dir, template_path, output_path):
    print(f"🚀 Starting full multi-source log processing... Target folder: {data_dir}")

    if not os.path.exists(data_dir):
        print(f"❌ Error: Monitoring data directory not found: {data_dir}")
        return

    # 1. 查找所有 Excel 文件并排序
    excel_files = sorted(glob.glob(os.path.join(data_dir, "*.xlsx")))
    if not excel_files:
        print(f"❌ Error: No .xlsx files found in {data_dir}")
        return
    print(f"📂 Found {len(excel_files)} data files. Starting sequential matrix parsing...")

    # ------------------------------------------------------------
    # 存储所有天的数据
    # ------------------------------------------------------------
    daily_data = []               # 每个元素是一个字典，包含该天的所有信息
    all_payment_types = set()     # 收集所有出现的支付类型

    # 用于最新一天快照
    latest_day_data = None

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        date_str = parse_date_from_filename(filename)   # e.g., "2026-05-28"
        date_label = format_date_label(date_str)

        print(f"   Processing {filename} ({date_label})")

        day_record = {
            'date': date_str,
            'date_label': date_label,
            'order_payment': {},     # paymentType -> {'orders': sum, 'revenue': sum}
            'kibana': {},            # 所有 Kibana 指标
            'fr_order': 0,
            'fr_cost': 0.0,
            'dynatrace_df': None,
            'quantummetric_df': None,
            'datahealth_df': None,
            'cronjob_df': None,
            'hotfolder_df': None,
            'bloomreach_df': None,
            'lighthouse_df': None,
        }

        try:
            # ---- OrderDistribution ----
            df_orders = pd.read_excel(file_path, sheet_name='OrderDistribution')
            # 按支付类型分组汇总
            grouped = df_orders.groupby('paymentType').agg({
                'orderCount': 'sum',
                'totalPriceWithoutTax': 'sum'
            }).reset_index()
            for _, row in grouped.iterrows():
                pt = row['paymentType']
                orders = int(row['orderCount'])
                revenue = float(row['totalPriceWithoutTax'])
                day_record['order_payment'][pt] = {'orders': orders, 'revenue': revenue}
                all_payment_types.add(pt)

            # ---- KibanaLog ----
            df_kibana = pd.read_excel(file_path, sheet_name='KibanaLog')
            # 假设只有一行数据
            if not df_kibana.empty:
                row = df_kibana.iloc[0]
                # 提取所有列，转换为字典，处理 NaN
                for col in df_kibana.columns:
                    val = row[col]
                    if pd.isna(val):
                        val = None
                    # 尝试转换为数字
                    if isinstance(val, (int, float)):
                        day_record['kibana'][col] = val
                    else:
                        day_record['kibana'][col] = str(val)
            else:
                day_record['kibana'] = {}

            # ---- FR-orders ----
            df_fr = pd.read_excel(file_path, sheet_name='FR-orders')
            if not df_fr.empty:
                day_record['fr_order'] = int(df_fr['FR Order Count'].iloc[0])
                day_record['fr_cost'] = float(df_fr['RemovalServiceCostSum'].iloc[0])

            # ---- 其他 Sheet（存储完整 DataFrame，便于模板渲染） ----
            day_record['dynatrace_df'] = pd.read_excel(file_path, sheet_name='Dynatrace')
            day_record['quantummetric_df'] = pd.read_excel(file_path, sheet_name='QuantumMetric')
            day_record['datahealth_df'] = pd.read_excel(file_path, sheet_name='DataHealth')
            day_record['cronjob_df'] = pd.read_excel(file_path, sheet_name='AllCronjobHealth')
            day_record['hotfolder_df'] = pd.read_excel(file_path, sheet_name='Hotfolder')
            day_record['bloomreach_df'] = pd.read_excel(file_path, sheet_name='Bloomreach')
            day_record['lighthouse_df'] = pd.read_excel(file_path, sheet_name='LighthouseProd')

            daily_data.append(day_record)
            latest_day_data = day_record  # 最后一个是最近的

        except Exception as e:
            print(f"⚠️ Warning: Error processing {filename}: {e}")
            continue

    if not daily_data:
        print("❌ No valid data extracted.")
        return

    # ------------------------------------------------------------
    # 整理数据用于模板
    # ------------------------------------------------------------
    # 日期列表（用于图表 X 轴）
    date_labels = [d['date_label'] for d in daily_data]

    # 支付类型顺序（与 test4.html 一致，并确保存在）
    payment_order = ['Acima', 'Affirm', 'amex', 'discover', 'GiftCard', 'mastercard', 'Paypal', 'visa', 'Synchrony', 'Fortiva', 'Klarna']
    # 补充可能缺失的类型
    for pt in all_payment_types:
        if pt not in payment_order:
            payment_order.append(pt)

    # 构建支付类型订单和收入的时间序列
    pay_order_series = {}
    pay_rev_series = {}
    for pt in payment_order:
        orders = []
        revs = []
        for day in daily_data:
            data = day['order_payment'].get(pt, {'orders': 0, 'revenue': 0.0})
            orders.append(data['orders'])
            revs.append(data['revenue'])
        pay_order_series[pt] = orders
        pay_rev_series[pt] = revs

    # 总订单和收入（总计）
    grand_total_orders = sum(sum(series) for series in pay_order_series.values())
    grand_total_rev = sum(sum(series) for series in pay_rev_series.values())

    # 计算总体 Cronjob 成功率（从所有天的数据累加）
    total_cronjobs_ran = 0
    total_cronjobs_success = 0
    for day in daily_data:
        df = day['cronjob_df']
        if not df.empty:
            total_cronjobs_ran += len(df)
            total_cronjobs_success += len(df[df['Status'].str.lower() == 'success'])
    cron_success_rate = (total_cronjobs_success / total_cronjobs_ran * 100) if total_cronjobs_ran > 0 else 100.0
    cron_failed = total_cronjobs_ran - total_cronjobs_success

    # Dynatrace 总计事件数
    total_dt_incidents = sum(len(day['dynatrace_df']) for day in daily_data)

    # 获取最新一天的数据用于顶部 KPI 等
    latest = daily_data[-1]
    last_day_orders = sum(day['order_payment'].get(pt, {}).get('orders', 0) for pt in payment_order)
    last_day_rev = sum(day['order_payment'].get(pt, {}).get('revenue', 0.0) for pt in payment_order)
    last_day_incidents = len(latest['dynatrace_df'])
    # Kibana 最新一天的指标
    kibana_latest = latest['kibana']
    last_day_failed_auths = kibana_latest.get('Failed payment authorization', 0)
    last_day_failed_captures = kibana_latest.get('Failed payment capture', 0)
    last_day_affirm_voids = kibana_latest.get('Affirm Void', 0)
    last_day_google_timeouts = kibana_latest.get('Google API timeout', 0)

    # 准备 FR 图表数据
    fr_dates = [d['date_label'] for d in daily_data]
    fr_orders = [d['fr_order'] for d in daily_data]
    fr_costs = [d['fr_cost'] for d in daily_data]

    # 准备 Kibana 堆叠图数据（取特定的四个指标）
    kibana_affirm_void = [d['kibana'].get('Affirm Void', 0) for d in daily_data]
    kibana_failed_capture = [d['kibana'].get('Failed payment capture', 0) for d in daily_data]
    kibana_failed_auth = [d['kibana'].get('Failed payment authorization', 0) for d in daily_data]
    kibana_google_timeout = [d['kibana'].get('Google API timeout', 0) for d in daily_data]

    # Dynatrace 分类汇总（所有天累计）
    dt_catalog_counts = {}
    for day in daily_data:
        df = day['dynatrace_df']
        if not df.empty and 'Catalog' in df.columns:
            for cat, cnt in df['Catalog'].fillna('Unknown').value_counts().to_dict().items():
                dt_catalog_counts[cat] = dt_catalog_counts.get(cat, 0) + cnt
    # 计算 API 百分比
    api_count = dt_catalog_counts.get('API', 0)
    api_pct = round((api_count / total_dt_incidents * 100), 1) if total_dt_incidents > 0 else 0

    # 准备 Lighthouse 最新一天的页面性能数据（用于表格/图表）
    latest_lighthouse_pages = []
    if latest and latest['lighthouse_df'] is not None:
        df_lh = latest['lighthouse_df']
        for _, row in df_lh.iterrows():
            latest_lighthouse_pages.append({
                'name': row.get('Page/Device Type', ''),
                'perf': int(row.get('Performance Score', 0)),
                'access': int(row.get('Accessibility Score', 0)),
                'best': int(row.get('Best Practices Score', 0)),
                'seo': int(row.get('SEO Score', 0))
            })

    # 准备其他表格的数据（最新一天）
    latest_dynatrace_rows = latest['dynatrace_df'].to_dict(orient='records') if latest['dynatrace_df'] is not None else []
    latest_quantum_rows = latest['quantummetric_df'].to_dict(orient='records') if latest['quantummetric_df'] is not None else []
    latest_datahealth_rows = latest['datahealth_df'].to_dict(orient='records') if latest['datahealth_df'] is not None else []
    latest_cronjob_rows = latest['cronjob_df'].to_dict(orient='records') if latest['cronjob_df'] is not None else []
    latest_hotfolder_rows = latest['hotfolder_df'].to_dict(orient='records') if latest['hotfolder_df'] is not None else []
    latest_bloomreach_rows = latest['bloomreach_df'].to_dict(orient='records') if latest['bloomreach_df'] is not None else []

    # 为支付类型表格准备行数据（包括日期列和每个支付类型的值）
    order_table_rows = []
    revenue_table_rows = []
    for i, day in enumerate(daily_data):
        row_order = {'date': day['date_label']}
        row_rev = {'date': day['date_label']}
        for pt in payment_order:
            data = day['order_payment'].get(pt, {'orders': 0, 'revenue': 0.0})
            row_order[pt] = data['orders']
            row_rev[pt] = data['revenue']
        order_table_rows.append(row_order)
        revenue_table_rows.append(row_rev)

    # 计算总计行
    total_order_row = {'date': 'Grand Total'}
    total_rev_row = {'date': 'Grand Total'}
    for pt in payment_order:
        total_orders = sum(row[pt] for row in order_table_rows)
        total_rev = sum(row[pt] for row in revenue_table_rows)
        total_order_row[pt] = total_orders
        total_rev_row[pt] = total_rev
    order_table_rows.append(total_order_row)
    revenue_table_rows.append(total_rev_row)

    # 准备 Kibana 表格行
    kibana_table_rows = []
    for day in daily_data:
        row = {'date': day['date_label']}
        # 从 kibana 字典复制所有列
        # 但为了保持与 test4.html 列顺序一致，我们可以定义固定列顺序
        columns = ['All Services Status', 'Cordial Rate Limit Exceeded (hits)', 'Cordial Email failure (order #)',
                   'Monitor Email Server Busy Issue', 'Versatile API Timed Out hits', 'Zip to Zone Mapping API Status',
                   'Zip to DeliveryZone Mapping Status', 'ECC Update Product to Hybris Issue', 'Invalid variant',
                   'Affirm Void', '# of Affirm Auth Timed out / # of failed Retry / # of Affirm 404 Error',
                   'Failed payment capture', 'Failed payment authorization', 'Google API timeout',
                   'Delivery zip code create/update', 'Vertex fallback']
        for col in columns:
            row[col] = day['kibana'].get(col, '-')
        kibana_table_rows.append(row)

    # 准备 AI 洞察（调用 OpenAI）
    print("🤖 Requesting Azure OpenAI multi-day operational insights...")
    try:
        client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION
        )
        prompt = (f"Write a professional English operational insight paragraph (150 words max, no markdown) "
                  f"for an e-commerce dashboard. Analysis across {len(daily_data)} days. "
                  f"Latest Day Orders: {last_day_orders}, Latest Day Revenue: ${last_day_rev:.2f}, Total Period Incidents: {total_dt_incidents}. "
                  f"Failed Auths yesterday: {last_day_failed_auths}. Inform if action is required.")
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        ai_insight = response.choices[0].message.content.strip()
    except Exception as ai_err:
        print(f"⚠️ OpenAI fallback active: {ai_err}")
        ai_insight = "Operational Insight: Core transactional flows remain stable with solid baseline revenue generation over the observed multi-day period. However, monitoring data shows sporadic failed payment authorizations. SRE teams should actively review gateway timeout thresholds to guarantee continuous front-end edge integrity."

    # ------------------------------------------------------------
    # 渲染模板
    # ------------------------------------------------------------
    print("🎨 Rendering HTML dashboard page using template_test4.html...")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        template = Template(template_content)

        # 构建所有传递给模板的数据
        context = {
            # 通用信息
            'snapshot_year': '2026',
            'daily_data': daily_data,
            'date_labels': date_labels,
            'payment_order': payment_order,
            # 顶部 KPI
            'total_orders_day': f"{last_day_orders:,}",
            'total_rev_day': f"${last_day_rev:,.2f}",
            'grand_total_orders': grand_total_orders,
            'grand_total_rev': grand_total_rev,
            'total_dt_incidents': total_dt_incidents,
            'api_percentage': api_pct,
            'cronjob_success_rate': f"{cron_success_rate:.1f}%",
            'cronjob_failed_count': cron_failed,
            # 表格数据
            'order_table_rows': order_table_rows,
            'revenue_table_rows': revenue_table_rows,
            'kibana_table_rows': kibana_table_rows,
            'latest_dynatrace_rows': latest_dynatrace_rows,
            'latest_quantum_rows': latest_quantum_rows,
            'latest_datahealth_rows': latest_datahealth_rows,
            'latest_cronjob_rows': latest_cronjob_rows,
            'latest_hotfolder_rows': latest_hotfolder_rows,
            'latest_bloomreach_rows': latest_bloomreach_rows,
            'latest_lighthouse_pages': latest_lighthouse_pages,
            # 图表数据
            'pay_order_series': pay_order_series,
            'pay_rev_series': pay_rev_series,
            'fr_dates': fr_dates,
            'fr_orders': fr_orders,
            'fr_costs': fr_costs,
            'kibana_affirm_void': kibana_affirm_void,
            'kibana_failed_capture': kibana_failed_capture,
            'kibana_failed_auth': kibana_failed_auth,
            'kibana_google_timeout': kibana_google_timeout,
            # 其他
            'ai_insight': ai_insight,
            # 最新一天的摘要数据
            'last_day_orders': last_day_orders,
            'last_day_rev': last_day_rev,
            'last_day_incidents': last_day_incidents,
            'last_day_failed_auths': last_day_failed_auths,
            'last_day_failed_captures': last_day_failed_captures,
            'last_day_affirm_voids': last_day_affirm_voids,
            'last_day_google_timeouts': last_day_google_timeouts,
        }

        rendered_html = template.render(**context)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        print(f"🎉 Success! Dashboard generated at: {output_path}")

    except Exception as e:
        print(f"❌ HTML rendering failed: {e}")

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_directory = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'

    target_data_dir = os.path.join(current_directory, "monitoring-data")
    # 使用基于 test4.html 的模板文件
    target_template_path = os.path.join(current_directory, "template_test4.html")
    target_output_path = os.path.join(current_directory, f"rm_daily_monitor_dashboard_{timestamp}.html")

    analyze_and_generate_report(
        data_dir=target_data_dir,
        template_path=target_template_path,
        output_path=target_output_path
    )