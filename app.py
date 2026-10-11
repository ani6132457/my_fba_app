import streamlit as st
import pandas as pd
from io import BytesIO
import uuid
from datetime import datetime, timedelta, timezone
import numpy as np

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
    df = df.sort_values("SKU")
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
    <tr>
        <th style='width:15%'>SKU</th>
        <th style='width:30%'>商品名</th>
        <th style='width:10%'>ASIN</th>
        <th style='width:10%'>FNSKU</th>
        <th style='width:10%'>数量</th>
        <th style='width:10%'>タイプ1</th>
        <th style='width:15%'>タイプ2</th>
    </tr>
    """
    for _, row in df.iterrows():
        t1 = row['タイプ1'] if pd.notna(row['タイプ1']) else ''
        t2 = row['タイプ2'] if pd.notna(row['タイプ2']) else ''
        asin = row['ASIN'] if pd.notna(row['ASIN']) else ''
        fnsku = row['FNSKU'] if pd.notna(row['FNSKU']) else ''
        html += f"<tr><td>{row['SKU']}</td><td class='wrap'>{row['商品名_x']}</td><td>{asin}</td><td>{fnsku}</td><td>{row['数量']}</td><td class='nowrap'>{t1}</td><td class='nowrap'>{t2}</td></tr>"
    html += f"</table><!-- {uuid.uuid4()} --></body></html>"
    return html

# 数量のマイナス変換（安全処理）
def safe_negate(value):
    try:
        return -int(value)
    except:
        return ""

if uploaded_file:
    # アップロードCSV読み込み（6行目がヘッダー）
    df_csv = pd.read_csv(uploaded_file, skiprows=5)

    # SKU前処理（空白など除去）
    df_csv['SKU'] = df_csv['SKU'].astype(str).str.strip()

    # SKUマスタとマージ
    merged_df = df_csv.merge(df_master, left_on="SKU", right_on="AmazonSKU", how="left")

    # Excelと同様のIF＋XLOOKUPロジックの再現
    merged_df["商品コード"] = merged_df.apply(
        lambda row: "" if row["SKU"] == "" else (row["テンポスターSKU"] if pd.notna(row["テンポスターSKU"]) else row["SKU"]),
        axis=1
    )

    stock_df = merged_df[["商品コード", "数量"]].copy()
    stock_df["数量"] = stock_df["数量"].apply(safe_negate)

    # 文字列"nan"、np.nan、NaNを完全に空文字に置換
    stock_df = stock_df.replace(["nan", "NaN", np.nan], "").astype(str)

    # 空白の行（商品コード・数量が両方空）を削除
    stock_df = stock_df[~((stock_df["商品コード"] == "") & (stock_df["数量"] == ""))]

    # 在庫アップロード用に2列目の項目名を「想定在庫数」に変更（値はマイナス数量のまま）
    stock_df = stock_df.rename(columns={"数量": "想定在庫数"})

    # Shift-JIS（Windows版：cp932）で出力
    csv_bytes = stock_df.to_csv(index=False).encode("cp932")

    # JST（日本時間）で現在時刻を取得してファイル名に使用
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST).strftime('%Y-%m-%d_%H-%M')
    file_name = f"在庫アップロードデータ_{now}.csv"

    st.download_button("📥 在庫アップロードCSVダウンロード", csv_bytes, file_name=file_name, mime="text/csv")

    # 印刷用ピッキングリストを表示（印刷ダイアログ自動起動）
    st.subheader("🖨 ワンクリック印刷：ピッキングリスト")
    if st.button("📄 ピッキングリストを印刷"):
        html_content = generate_auto_print_html(merged_df)
        st.components.v1.html(html_content, height=1500, scrolling=True)
