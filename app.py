import streamlit as st
import pandas as pd
from io import BytesIO
import pdfkit
import tempfile
import os

st.title("FBA業務支援アプリ（CSVアップロード・出力）")

# 1. CSVアップロード（貼り付け相当）
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

# 2. SKU対応表は固定ファイルから読み込む（アップロード不要）
sku_master_path = "data/sku_master.xlsx"
df_master = pd.read_excel(sku_master_path)

# PDF用のHTMLテンプレート関数（PDFKit向け）
def create_picking_html(df):
    df = df[df['SKU'].notna() & df['商品名_x'].notna()]  # NaNの輸送箱情報は除外
    html = """
    <html><head>
    <meta charset='utf-8'>
    <style>
    @media print {
        body { font-family: 'Yu Gothic', sans-serif; font-size: 10pt; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #333; padding: 4px; }
        th { background-color: #f0f0f0; }
        td.wrap { word-wrap: break-word; white-space: normal; }
        td.nowrap { white-space: nowrap; }
    }
    .page-break { page-break-after: always; }
    </style></head><body>
    """
    for i in range(0, len(df), 20):
        page = df.iloc[i:i+20]
        html += "<table>"
        html += "<tr><th style='width:15%'>SKU</th><th style='width:45%'>商品名</th><th style='width:10%'>数量</th><th style='width:15%'>タイプ1</th><th style='width:15%'>タイプ2</th></tr>"
        for _, row in page.iterrows():
            t1 = row['タイプ1'] if pd.notna(row['タイプ1']) else ''
            t2 = row['タイプ2'] if pd.notna(row['タイプ2']) else ''
            html += f"<tr><td>{row['SKU']}</td><td class='wrap'>{row['商品名_x']}</td><td>{row['数量']}</td><td class='nowrap'>{t1}</td><td class='nowrap'>{t2}</td></tr>"
        html += "</table><div class='page-break'></div>"
    html += "</body></html>"
    return html

if uploaded_file:
    # 読み込み（6行目がヘッダー）
    df_csv = pd.read_csv(uploaded_file, skiprows=5)

    # マージ
    merged_df = df_csv.merge(df_master, left_on="SKU", right_on="AmazonSKU", how="left")

    # CSV出力（在庫アップロードデータ形式）
    stock_df = merged_df[merged_df['SKU'].notna()][["テンポスターSKU", "数量"]].copy()
    stock_df["数量"] = stock_df["数量"].apply(lambda x: -int(x) if pd.notna(x) else "")
    stock_df.columns = ["商品コード", "想定在庫数"]

    csv_buffer = BytesIO()
    stock_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    st.download_button("📥 在庫アップロードCSVダウンロード", csv_buffer.getvalue(), file_name="在庫アップロードデータ.csv", mime="text/csv")

    # PDF出力ボタン（PDFKit）
    if st.button("📄 ピッキングリストPDF作成"):
        html = create_picking_html(merged_df)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            pdf_path = f.name
        config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
        pdfkit.from_string(html, pdf_path, configuration=config)

        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 ピッキングリストをダウンロード",
                data=f.read(),
                file_name="ピッキングリスト.pdf",
                mime="application/pdf"
            )
        os.remove(pdf_path)
