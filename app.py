import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")
st.title("FBA業務支援アプリ（CSV出力＋印刷表示）")

# CSVアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

# SKU対応表の読み込み（固定ファイル）
sku_master_path = "data/sku_master.xlsx"
df_master = pd.read_excel(sku_master_path)

# HTML保存と表示リンク作成
def save_html_and_get_url(html):
    html_path = "/tmp/picking_list.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"<a href='picking_list.html' target='_blank'>🖨 ピッキングリストを別タブで開く</a>"

# 印刷用HTMLを生成
def generate_html_table(df):
    df = df[df['SKU'].notna() & df['商品名_x'].notna()]
    html = """
    <html><head><meta charset='utf-8'>
    <style>
    @media print {
        body { font-family: 'Yu Gothic', sans-serif; font-size: 10pt; }
        table { width: 100%; border-collapse: collapse; page-break-after: always; }
        th, td { border: 1px solid #333; padding: 4px; }
        th { background-color: #f0f0f0; }
        td.wrap { word-wrap: break-word; white-space: normal; }
        td.nowrap { white-space: nowrap; }
    }
    </style></head><body>
    <h3>ピッキングリスト</h3>
    <table>
    <tr><th style='width:15%'>SKU</th><th style='width:45%'>商品名</th><th style='width:10%'>数量</th><th style='width:15%'>タイプ1</th><th style='width:15%'>タイプ2</th></tr>
    """
    for _, row in df.iterrows():
        t1 = row['タイプ1'] if pd.notna(row['タイプ1']) else ''
        t2 = row['タイプ2'] if pd.notna(row['タイプ2']) else ''
        html += f"<tr><td>{row['SKU']}</td><td class='wrap'>{row['商品名_x']}</td><td>{row['数量']}</td><td class='nowrap'>{t1}</td><td class='nowrap'>{t2}</td></tr>"
    html += "</table></body></html>"
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
    st.download_button("📥 在庫アップロードCSVダウンロード", csv_buffer.getvalue(), file_name="在庫アップロードデータ.csv", mime="text/csv")

    # 印刷表示リンク（別タブ）
    st.subheader("🖨 ピッキングリスト（別タブで開く）")
    html_content = generate_html_table(merged_df)
    st.components.v1.html(save_html_and_get_url(html_content), height=50, scrolling=False)
