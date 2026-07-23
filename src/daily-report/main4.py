import os
import glob
import pandas as pd
from jinja2 import Template
from openai import AzureOpenAI
from config import *
from datetime import datetime
import re

def parse_date_from_filename(filename):
    """Parse date string from filename like '05282026.xlsx' -> '2026-05-28'"""
    base = os.path.splitext(filename)[0]
    if len(base) == 8 and base.isdigit():
        month = base[:2]
        day = base[2:4]
        year = base[4:8]
        return f"{year}-{month}-{day}"
    return base

def format_date_label(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%m/%d/%Y")
    except:
        return date_str

def safe_str(val):
    """Return '-' if val is empty, NaN, or None; else return str(val)"""
    if val is None or (isinstance(val, float) and pd.isna(val)) or val == "" or val == "nan":
        return "-"
    return str(val)

def analyze_and_generate_report(data_dir, template_path, output_path):
    print(f"🚀 Starting full multi-source log processing... Target folder: {data_dir}")

    if not os.path.exists(data_dir):
        print(f"❌ Error: Monitoring data directory not found: {data_dir}")
        return

    excel_files = sorted(glob.glob(os.path.join(data_dir, "*.xlsx")))
    if not excel_files:
        print(f"❌ Error: No .xlsx files found in {data_dir}")
        return
    print(f"📂 Found {len(excel_files)} data files. Starting sequential matrix parsing...")

    daily_data = []
    all_payment_types = set()
    latest_day_data = None

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        date_str = parse_date_from_filename(filename)
        date_label = format_date_label(date_str)
        print(f"   Processing {filename} ({date_label})")

        day_record = {
            'date': date_str,
            'date_label': date_label,
            'order_payment': {},
            'kibana': {},
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
            if not df_kibana.empty:
                row = df_kibana.iloc[0]
                for col in df_kibana.columns:
                    val = row[col]
                    if pd.isna(val):
                        val = None
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

            # ---- Other sheets ----
            day_record['dynatrace_df'] = pd.read_excel(file_path, sheet_name='Dynatrace')
            day_record['quantummetric_df'] = pd.read_excel(file_path, sheet_name='QuantumMetric')
            day_record['datahealth_df'] = pd.read_excel(file_path, sheet_name='DataHealth')
            day_record['cronjob_df'] = pd.read_excel(file_path, sheet_name='AllCronjobHealth')
            day_record['hotfolder_df'] = pd.read_excel(file_path, sheet_name='Hotfolder')
            day_record['bloomreach_df'] = pd.read_excel(file_path, sheet_name='Bloomreach')
            day_record['lighthouse_df'] = pd.read_excel(file_path, sheet_name='LighthouseProd')

            daily_data.append(day_record)
            latest_day_data = day_record

        except Exception as e:
            print(f"⚠️ Warning: Error processing {filename}: {e}")
            continue

    if not daily_data:
        print("❌ No valid data extracted.")
        return

    # ========== Data preparation ==========
    date_labels = [d['date_label'] for d in daily_data]

    # Payment types order (include all found)
    payment_order = ['Acima', 'Affirm', 'amex', 'discover', 'GiftCard', 'mastercard', 'Paypal', 'visa', 'Synchrony', 'Fortiva', 'Klarna']
    for pt in all_payment_types:
        if pt not in payment_order:
            payment_order.append(pt)

    # Build time series for orders and revenue per payment type
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

    # Grand totals
    grand_total_orders = sum(sum(series) for series in pay_order_series.values())
    grand_total_rev = sum(sum(series) for series in pay_rev_series.values())

    # Totals by payment type (for grand total row)
    total_by_pay_order = {pt: sum(pay_order_series[pt]) for pt in payment_order}
    total_by_pay_rev = {pt: sum(pay_rev_series[pt]) for pt in payment_order}

    # Cronjob stats
    total_cronjobs_ran = 0
    total_cronjobs_success = 0
    for day in daily_data:
        df = day['cronjob_df']
        if not df.empty:
            total_cronjobs_ran += len(df)
            total_cronjobs_success += len(df[df['Status'].str.lower() == 'success'])
    cron_success_rate = (total_cronjobs_success / total_cronjobs_ran * 100) if total_cronjobs_ran > 0 else 100.0
    cron_failed = total_cronjobs_ran - total_cronjobs_success

    # Dynatrace incidents total
    total_dt_incidents = sum(len(day['dynatrace_df']) for day in daily_data)

    # Latest day data
    latest = daily_data[-1]
    last_day_orders = sum(latest['order_payment'].get(pt, {}).get('orders', 0) for pt in payment_order)
    last_day_rev = sum(latest['order_payment'].get(pt, {}).get('revenue', 0.0) for pt in payment_order)
    last_day_incidents = len(latest['dynatrace_df'])
    kibana_latest = latest['kibana']
    last_day_failed_auths = kibana_latest.get('Failed payment authorization', 0)
    last_day_failed_captures = kibana_latest.get('Failed payment capture', 0)
    last_day_affirm_voids = kibana_latest.get('Affirm Void', 0)
    last_day_google_timeouts = kibana_latest.get('Google API timeout', 0)

    # FR data
    fr_dates = [d['date_label'] for d in daily_data]
    fr_orders = [d['fr_order'] for d in daily_data]
    fr_costs_numeric = [d['fr_cost'] for d in daily_data]
    fr_costs_formatted = [f"${c:,.2f}" for c in fr_costs_numeric]

    # Kibana stacked chart data
    kibana_affirm_void = [d['kibana'].get('Affirm Void', 0) for d in daily_data]
    kibana_failed_capture = [d['kibana'].get('Failed payment capture', 0) for d in daily_data]
    kibana_failed_auth = [d['kibana'].get('Failed payment authorization', 0) for d in daily_data]
    kibana_google_timeout = [d['kibana'].get('Google API timeout', 0) for d in daily_data]

    # Dynatrace catalog breakdown
    dt_catalog_counts = {}
    for day in daily_data:
        df = day['dynatrace_df']
        if not df.empty and 'Catalog' in df.columns:
            for cat, cnt in df['Catalog'].fillna('Unknown').value_counts().to_dict().items():
                dt_catalog_counts[cat] = dt_catalog_counts.get(cat, 0) + cnt
    api_count = dt_catalog_counts.get('API', 0)
    api_pct = round((api_count / total_dt_incidents * 100), 1) if total_dt_incidents > 0 else 0

    # Prepare table rows with empty values replaced by "-"
    def clean_row_dict(row_dict):
        return {k: safe_str(v) for k, v in row_dict.items()}

    # Order and Revenue tables
    order_table_rows = []
    revenue_table_rows = []
    for i, day in enumerate(daily_data):
        row_order = {'date': day['date_label']}
        row_rev = {'date': day['date_label']}
        total_orders = 0
        total_rev = 0.0
        for pt in payment_order:
            data = day['order_payment'].get(pt, {'orders': 0, 'revenue': 0.0})
            row_order[pt] = f"{data['orders']:,}"
            row_rev[pt] = f"${data['revenue']:,.2f}"
            total_orders += data['orders']
            total_rev += data['revenue']
        row_order['total'] = f"{total_orders:,}"
        row_rev['total'] = f"${total_rev:,.2f}"
        order_table_rows.append(clean_row_dict(row_order))
        revenue_table_rows.append(clean_row_dict(row_rev))

    # Grand total rows
    total_order_row = {'date': 'Grand Total'}
    total_rev_row = {'date': 'Grand Total'}
    for pt in payment_order:
        total_order_row[pt] = f"{total_by_pay_order[pt]:,}"
        total_rev_row[pt] = f"${total_by_pay_rev[pt]:,.2f}"
    total_order_row['total'] = f"{grand_total_orders:,}"
    total_rev_row['total'] = f"${grand_total_rev:,.2f}"
    order_table_rows.append(clean_row_dict(total_order_row))
    revenue_table_rows.append(clean_row_dict(total_rev_row))

    # Kibana table rows
    kibana_columns = ['All Services Status', 'Cordial Rate Limit Exceeded (hits)', 'Cordial Email failure (order #)',
                      'Monitor Email Server Busy Issue', 'Versatile API Timed Out hits', 'Zip to Zone Mapping API Status',
                      'Zip to DeliveryZone Mapping Status', 'ECC Update Product to Hybris Issue', 'Invalid variant',
                      'Affirm Void', '# of Affirm Auth Timed out / # of failed Retry / # of Affirm 404 Error',
                      'Failed payment capture', 'Failed payment authorization', 'Google API timeout',
                      'Delivery zip code create/update', 'Vertex fallback']
    kibana_table_rows = []
    for day in daily_data:
        row = {'date': day['date_label']}
        for col in kibana_columns:
            val = day['kibana'].get(col, '-')
            row[col] = safe_str(val)
        kibana_table_rows.append(row)

    # ---- Build all QuantumMetric and Dynatrace rows across all days ----
    all_quantum_rows = []
    all_dynatrace_rows = []

    for day in daily_data:
        df_q = day['quantummetric_df']
        if df_q is not None and not df_q.empty:
            for _, row in df_q.iterrows():
                row_dict = row.to_dict()
                row_dict['date'] = day['date_label']
                all_quantum_rows.append(clean_row_dict(row_dict))

        df_d = day['dynatrace_df']
        if df_d is not None and not df_d.empty:
            for _, row in df_d.iterrows():
                row_dict = row.to_dict()
                row_dict['date'] = day['date_label']
                all_dynatrace_rows.append(clean_row_dict(row_dict))

    # Latest day rows for other tables (DataHealth, Cronjob, Hotfolder, Bloomreach) – still needed
    latest_datahealth_rows = [clean_row_dict(row) for row in latest['datahealth_df'].to_dict(orient='records')] if latest['datahealth_df'] is not None else []
    latest_cronjob_rows = [clean_row_dict(row) for row in latest['cronjob_df'].to_dict(orient='records')] if latest['cronjob_df'] is not None else []
    latest_hotfolder_rows = [clean_row_dict(row) for row in latest['hotfolder_df'].to_dict(orient='records')] if latest['hotfolder_df'] is not None else []
    latest_bloomreach_rows = [clean_row_dict(row) for row in latest['bloomreach_df'].to_dict(orient='records')] if latest['bloomreach_df'] is not None else []

    # Latest two days comparison for summary
    if len(daily_data) >= 2:
        prev_day = daily_data[-2]
        last_day = daily_data[-1]
        prev_date = prev_day['date_label']
        last_date = last_day['date_label']

        prev_orders = sum(prev_day['order_payment'].get(pt, {}).get('orders', 0) for pt in payment_order)
        last_orders = sum(last_day['order_payment'].get(pt, {}).get('orders', 0) for pt in payment_order)
        prev_rev = sum(prev_day['order_payment'].get(pt, {}).get('revenue', 0.0) for pt in payment_order)
        last_rev = sum(last_day['order_payment'].get(pt, {}).get('revenue', 0.0) for pt in payment_order)

        order_change = last_orders - prev_orders
        rev_change = last_rev - prev_rev
        order_pct = (order_change / prev_orders * 100) if prev_orders else 0
        rev_pct = (rev_change / prev_rev * 100) if prev_rev else 0

        prev_orders_display = f"{prev_orders:,}"
        last_orders_display = f"{last_orders:,}"
        prev_rev_display = f"${prev_rev:,.2f}"
        last_rev_display = f"${last_rev:,.2f}"
        order_pct_str = f"{order_pct:+.2f}%"
        rev_pct_str = f"{rev_pct:+.2f}%"
        order_arrow = "up" if order_change >= 0 else "down"
        rev_arrow = "up" if rev_change >= 0 else "down"
    else:
        prev_date = last_date = date_labels[0] if date_labels else ""
        prev_orders_display = last_orders_display = "0"
        prev_rev_display = last_rev_display = "$0.00"
        order_pct_str = rev_pct_str = "0.00%"
        order_arrow = rev_arrow = "up"

    # ========== AI Insight ==========
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

    # ========== Render Template ==========
    print("🎨 Rendering HTML dashboard page using template_test4.html...")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        template = Template(template_content)

        context = {
            'snapshot_year': '2026',
            'daily_data': daily_data,
            'date_labels': date_labels,
            'payment_order': payment_order,
            # KPI (formatted)
            'total_orders_day': f"{last_day_orders:,}",
            'total_rev_day': f"${last_day_rev:,.2f}",
            'grand_total_orders_fmt': f"{grand_total_orders:,}",
            'grand_total_rev_fmt': f"${grand_total_rev:,.2f}",
            'total_dt_incidents': total_dt_incidents,
            'api_percentage': api_pct,
            'cronjob_success_rate': f"{cron_success_rate:.1f}%",
            'cronjob_failed_count': cron_failed,
            # Table data
            'order_table_rows': order_table_rows,
            'revenue_table_rows': revenue_table_rows,
            'kibana_table_rows': kibana_table_rows,
            'all_quantum_rows': all_quantum_rows,
            'all_dynatrace_rows': all_dynatrace_rows,
            'latest_datahealth_rows': latest_datahealth_rows,
            'latest_cronjob_rows': latest_cronjob_rows,
            'latest_hotfolder_rows': latest_hotfolder_rows,
            'latest_bloomreach_rows': latest_bloomreach_rows,
            # Chart data (as JSON)
            'pay_order_series': pay_order_series,
            'pay_rev_series': pay_rev_series,
            'fr_dates': fr_dates,
            'fr_orders': fr_orders,
            'fr_costs': fr_costs_numeric,        # numeric for chart
            'fr_costs_formatted': fr_costs_formatted, # for display
            'kibana_affirm_void': kibana_affirm_void,
            'kibana_failed_capture': kibana_failed_capture,
            'kibana_failed_auth': kibana_failed_auth,
            'kibana_google_timeout': kibana_google_timeout,
            # AI and summary
            'ai_insight': ai_insight,
            'last_day_orders': last_day_orders,
            'last_day_rev': last_day_rev,
            'last_day_incidents': last_day_incidents,
            'last_day_failed_auths': last_day_failed_auths,
            'last_day_failed_captures': last_day_failed_captures,
            'last_day_affirm_voids': last_day_affirm_voids,
            'last_day_google_timeouts': last_day_google_timeouts,
            # Comparison summary
            'prev_date': prev_date,
            'last_date': last_date,
            'prev_orders_display': prev_orders_display,
            'last_orders_display': last_orders_display,
            'prev_rev_display': prev_rev_display,
            'last_rev_display': last_rev_display,
            'order_pct_str': order_pct_str,
            'rev_pct_str': rev_pct_str,
            'order_arrow': order_arrow,
            'rev_arrow': rev_arrow,
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
    target_template_path = os.path.join(current_directory, "template_test4.html")
    target_output_path = os.path.join(current_directory, f"rm_daily_monitor_dashboard_{timestamp}.html")

    analyze_and_generate_report(
        data_dir=target_data_dir,
        template_path=target_template_path,
        output_path=target_output_path
    )