import streamlit as st
import pandas as pd
from io import BytesIO
import uuid
from datetime import datetime

st.set_page_config(layout="wide")
st.title("FBA業務支援アプリ（CSV出力＋印刷表示）")

# CSVアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

# SKU対応表の読み込み（固定ファイル）
sku_master_path = "data/sku_master.xlsx"
df_master = pd.read_excel(sku_master_path)

# 印刷用HTML（自動で印刷ダイアログが開く）
def generate_auto_print_html(df):
    df = df[df['SKU'].notna() & df['商品名_x'].notna()]
    html = """
    <html><head><meta charset='utf-8'>
    <script>window.onload = function() { window.print(); }</script>
    <style>
    body { font-family: 'Yu Gothic', sans-serif; font-size: 10pt; }
    table { width: 100%; border-collapse: collapse; page-break-after: always; }
    th, td { border: 1px solid #333; padding: 4px; }
    th { background-color: #f0f0f0; }
    td.wrap { word-wrap: break-word; white-space: normal; }
    td.nowrap { white-space: nowrap; }
    </style></head><body>
    <h3>ピッキングリスト</h3>
    <table>
    <tr><th style='width:15%'>SKU</th><th style='width:45%'>商品名</th><th style='width:10%'>数量</th><th style='width:15%'>タイプ1</th><th style='width:15%'>タイプ2</th></tr>
    """
    for _, row in df.iterrows():
        t1 = row['タイプ1'] if pd.notna(row['タイプ1']) else ''
        t2 = row['タイプ2'] if pd.notna(row['タイプ2']) else ''
        html += f"<tr><td>{row['SKU']}</td><td class='wrap'>{row['商品名_x']}</td><td>{row['数量']}</td><td class='nowrap'>{t1}</td><td class='nowrap'>{t2}</td></tr>"
    html += f"</table><!-- {uuid.uuid4()} --></body></html>"
    return html

if uploaded_file:
    # アップロードCSV読み込み（6行目がヘッダー）
    df_csv = pd.read_csv(uploaded_file, skiprows=5)

    # SKUマスタとマージ
    merged_df = df_csv.merge(df_master, left_on="SKU", right_on="AmazonSKU", how="left")

    # 在庫アップロード用CSV出力
    stock_df = merged_df[merged_df['SKU'].notna()][["テンポスターSKU", "数量"]].copy()
    stock_df["数量"] = stock_df["数量"].apply(lambda x: -int(x) if pd.notna(x) else "")
    stock_df.columns = ["商品コード", "想定在庫数"]

    csv_buffer = BytesIO()
    stock_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")

    # 日付＋時間付きファイル名
    now = datetime.now().strftime('%Y-%m-%d_%H-%M')
    file_name = f"在庫アップロードデータ_{now}.csv"

    st.download_button("📥 在庫アップロードCSVダウンロード", csv_buffer.getvalue(), file_name=file_name, mime="text/csv")

    # 印刷用ピッキングリストを表示（印刷ダイアログ自動起動）
    st.subheader("🖨 ワンクリック印刷：ピッキングリスト")
    if st.button("📄 ピッキングリストを印刷"):
        html_content = generate_auto_print_html(merged_df)
        st.components.v1.html(html_content, height=1500, scrolling=True)
