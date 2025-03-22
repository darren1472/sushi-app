import streamlit as st
import pandas as pd
import math
import io
import os
from datetime import datetime, timedelta
import pdfkit  # ※ wkhtmltopdf のインストールが必要です
import tempfile

# --- ページ設定 ---
st.set_page_config(
    page_title="寿司製造管理システム",
    page_icon="🍣",
    layout="wide"  # 画面を広く使用
)

# =====================================================
# データ定義（寿司セット、原価、在庫保存用）
# =====================================================
set_recipes = {
    "極上セット": {"マグロ": 3, "サーモン": 2, "イカ": 1, "玉子": 1, "エビ": 2, "ホタテ": 1},
    "季節の彩りセット": {"マグロ": 2, "サーモン": 2, "イカ": 2, "玉子": 1, "エビ": 1, "ホタテ": 1},
    "まかない寿司セット": {"マグロ": 1, "サーモン": 1, "イカ": 1, "玉子": 2, "エビ": 0, "ホタテ": 0},
    "穴子押し寿司": {"マグロ": 0, "サーモン": 0, "イカ": 0, "玉子": 0, "エビ": 0, "ホタテ": 0}
}

set_prices = {
    "極上セット": 1480,
    "季節の彩りセット": 1280,
    "まかない寿司セット": 698,
    "穴子押し寿司": 980
}

order_lot = {
    "マグロ": 20,
    "サーモン": 30,
    "イカ": 20,
    "玉子": 10,
    "エビ": 15,
    "ホタテ": 10
}

ingredients = ["マグロ", "サーモン", "イカ", "玉子", "エビ", "ホタテ"]

# 各ネタの原価（単価）【例として設定】
ingredient_cost = {
    "マグロ": 300,
    "サーモン": 250,
    "イカ": 100,
    "玉子": 50,
    "エビ": 150,
    "ホタテ": 200
}

# =====================================================
# 在庫データの永続化（CSVファイル）用関数
# =====================================================
def load_inventory():
    if os.path.exists("inventory.csv"):
        try:
            df = pd.read_csv("inventory.csv", encoding="utf-8-sig")
            return {row["ネタ"]: int(row["在庫枚数"]) for index, row in df.iterrows()}
        except Exception as e:
            st.error(f"在庫データの読み込みに失敗しました: {e}")
            return {ing: 0 for ing in ingredients}
    else:
        return {ing: 0 for ing in ingredients}

def save_inventory_to_csv(inventory):
    try:
        df = pd.DataFrame(list(inventory.items()), columns=["ネタ", "在庫枚数"])
        df.to_csv("inventory.csv", index=False, encoding="utf-8-sig")
        st.success("在庫データが CSV ファイルに保存されました。")
    except Exception as e:
        st.error(f"在庫データの保存に失敗しました: {e}")

# =====================================================
# CSSスタイル（高齢者向け・高コントラスト・大きなボタンなど）
# =====================================================
st.markdown(
    """
    <style>
    .stApp { font-size: 20px; }
    input[type="number"] { font-size: 22px !important; height: 50px !important; }
    .stButton button { font-size: 24px !important; padding: 15px !important; border-radius: 10px !important; font-weight: bold !important; background-color: #4CAF50 !important; color: white !important; box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #ffffff; }
    th, td { border: 2px solid #dddddd; text-align: center; padding: 15px; font-size: 22px; color: #000000; }
    th { background-color: #4CAF50; color: white; font-weight: bold; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    tr:nth-child(odd) { background-color: #ffffff; }
    label { font-size: 22px !important; font-weight: bold !important; color: #333333 !important; }
    h1, h2, h3 { color: #2E4053 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 20px; font-weight: bold; background-color: #f0f8ff; border-radius: 10px 10px 0 0; padding: 10px 16px; }
    .stTabs [aria-selected="true"] { background-color: #4CAF50 !important; color: white !important; }
    .stNumberInput { margin-bottom: 20px; }
    .stAlert { font-size: 20px !important; padding: 20px !important; border-radius: 10px !important; }
    @media print {
        .stButton, .stDownloadButton, footer, header, .stTabs { display: none !important; }
        .print-only { display: block !important; }
        body { font-size: 24px !important; }
        table { border: 3px solid black !important; }
        th, td { border: 2px solid black !important; padding: 12px !important; font-size: 22px !important; }
    }
    </style>
    """, unsafe_allow_html=True
)

# =====================================================
# セッション状態の初期化
# =====================================================
if 'today_report' not in st.session_state:
    st.session_state['today_report'] = None
if 'tomorrow_required' not in st.session_state:
    st.session_state['tomorrow_required'] = None
if 'current_inventory' not in st.session_state:
    st.session_state['current_inventory'] = load_inventory()  # CSVから読み込み

# =====================================================
# サイドバー：ユーザーログイン（シンプルな認証）
# =====================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

with st.sidebar:
    st.header("ユーザーログイン")
    if not st.session_state.logged_in:
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if username == "admin" and password == "password":
                st.session_state.logged_in = True
                st.success("ログイン成功！")
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")
    else:
        st.info("ようこそ、adminさん！")

# =====================================================
# タブの作成（7タブ：既存の5タブ＋売上予測・原価計算）
# =====================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "① 今日の製造計画",
    "② 明日の製造計画",
    "③ 在庫入力",
    "④ 発注計算",
    "⑤ 印刷用レポート",
    "⑥ 売上予測",
    "⑦ 原価計算"
])

# =====================================================
# タブ①：今日の製造計画（原価計算含む）
# =====================================================
with tab1:
    st.header("① 今日の製造計画")
    st.markdown("### 各セットの製造数を入力し、「今日の計画を計算」ボタンを押してください。")
    
    # セット内容表示
    st.markdown("#### 🔍 セット内容の確認")
    set_info = []
    for set_name, recipe in set_recipes.items():
        price = set_prices.get(set_name, 0)
        neta_info = ", ".join([f"{ing}: {count}枚" for ing, count in recipe.items() if count > 0])
        if not neta_info:
            neta_info = "特別品"
        set_info.append({
            "セット名": set_name,
            "使用ネタ": neta_info,
            "販売価格": f"¥{price:,}"
        })
    df_set_info = pd.DataFrame(set_info)
    st.table(df_set_info)
    
    st.markdown("---")
    st.markdown("#### 📝 製造数の入力")
    col1, col2 = st.columns(2)
    today_plan = {}
    for i, set_name in enumerate(set_recipes.keys()):
        with col1 if i % 2 == 0 else col2:
            today_plan[set_name] = st.number_input(
                f"📦 {set_name} の製造数", 
                min_value=0, value=0, step=1, key=f"today_{set_name}"
            )
    
    st.markdown("---")
    if st.button("✅ 今日の計画を計算", key="calc_today", use_container_width=True):
        try:
            today_summary = []
            total_production_money = 0
            total_production_cost = 0
            ingredient_usage = {ing: 0 for ing in ingredients}
            
            for set_name, count in today_plan.items():
                if count > 0:
                    price = set_prices.get(set_name, 0)
                    money = count * price
                    total_production_money += money
                    # 原価計算
                    cost_per_set = sum(set_recipes[set_name][ing] * ingredient_cost[ing] for ing in ingredients)
                    total_cost = cost_per_set * count
                    total_production_cost += total_cost
                    today_summary.append({
                        "セット名": set_name,
                        "製造数": count,
                        "販売単価": f"¥{price:,}",
                        "製造金額": f"¥{money:,}",
                        "原価": f"¥{total_cost:,}",
                        "利益": f"¥{money - total_cost:,}"
                    })
                    # 使用ネタ集計
                    for ing, req in set_recipes[set_name].items():
                        ingredient_usage[ing] += req * count
            
            if today_summary:
                st.markdown("### 📊 今日の製造集計")
                df_today = pd.DataFrame(today_summary)
                st.table(df_today)
                st.markdown(f"### 💰 合計製造金額: ¥{total_production_money:,}")
                st.markdown(f"### 🛒 合計原価: ¥{total_production_cost:,}")
                st.markdown(f"### 💡 推定利益: ¥{total_production_money - total_production_cost:,}")
                
                st.markdown("### 🔪 使用ネタ集計")
                usage_data = [(ing, count) for ing, count in ingredient_usage.items() if count > 0]
                if usage_data:
                    df_usage = pd.DataFrame(usage_data, columns=["ネタ", "使用枚数"])
                    st.table(df_usage)
                else:
                    st.info("使用するネタはありません。")
                
                current_date = datetime.now().strftime("%Y年%m月%d日")
                st.session_state["today_report"] = {
                    "date": current_date,
                    "summary": today_summary,
                    "total_money": total_production_money,
                    "total_cost": total_production_cost,
                    "usage": ingredient_usage
                }
                st.success("印刷用レポート（タブ⑤）に反映されました。")
            else:
                st.warning("製造数がすべて0でした。数字を入力してください。")
        except Exception as e:
            st.error(f"計算中にエラーが発生しました: {e}")

# =====================================================
# タブ②：明日の製造計画
# =====================================================
with tab2:
    st.header("② 明日の製造計画")
    st.markdown("### 各セットの明日の製造目標数を入力し、「明日の計画を計算」ボタンを押してください。")
    
    st.markdown("#### 🔍 セット内容の確認")
    st.table(df_set_info)
    
    st.markdown("---")
    st.markdown("#### 📝 製造目標数の入力")
    col1, col2 = st.columns(2)
    tomorrow_plan = {}
    for i, set_name in enumerate(set_recipes.keys()):
        with col1 if i % 2 == 0 else col2:
            tomorrow_plan[set_name] = st.number_input(
                f"📦 {set_name} の製造目標数", 
                min_value=0, value=0, step=1, key=f"tomorrow_{set_name}"
            )
    
    st.markdown("---")
    if st.button("✅ 明日の計画を計算", key="calc_tomorrow", use_container_width=True):
        try:
            ingredient_required = {ing: 0 for ing in ingredients}
            total_target_money = 0
            tomorrow_summary = []
            
            for set_name, count in tomorrow_plan.items():
                if count > 0:
                    price = set_prices.get(set_name, 0)
                    money = count * price
                    total_target_money += money
                    tomorrow_summary.append({
                        "セット名": set_name,
                        "製造目標数": count,
                        "販売単価": f"¥{price:,}",
                        "目標製造金額": f"¥{money:,}"
                    })
                    for ing, req in set_recipes[set_name].items():
                        ingredient_required[ing] += req * count
            
            if tomorrow_summary:
                st.markdown("### 📊 明日の製造目標")
                df_tomorrow = pd.DataFrame(tomorrow_summary)
                st.table(df_tomorrow)
                st.markdown(f"### 💰 合計目標製造金額: ¥{total_target_money:,}")
                
                st.markdown("### 🔪 明日の必要ネタ数")
                required_data = [(ing, count) for ing, count in ingredient_required.items() if count > 0]
                if required_data:
                    df_required = pd.DataFrame(required_data, columns=["ネタ", "必要枚数"])
                    st.table(df_required)
                else:
                    st.info("必要なネタはありません。")
                
                st.session_state["tomorrow_required"] = ingredient_required
                st.session_state["tomorrow_summary"] = tomorrow_summary
                st.session_state["tomorrow_total"] = total_target_money
                st.success("在庫入力（タブ③）・発注計算（タブ④）で使用されます。")
            else:
                st.warning("すべて0でした。数字を入力してください。")
        except Exception as e:
            st.error(f"計算中にエラーが発生しました: {e}")

# =====================================================
# タブ③：在庫入力（データ永続化対応）
# =====================================================
with tab3:
    st.header("③ 在庫入力")
    st.markdown("### 現在の各ネタの在庫数を入力してください。（製造終了後の残数など）")
    
    st.markdown("#### 📝 在庫枚数の入力")
    col1, col2 = st.columns(2)
    current_inventory = {}
    for i, ing in enumerate(ingredients):
        with col1 if i % 2 == 0 else col2:
            current_inventory[ing] = st.number_input(
                f"🍣 {ing} の在庫枚数", 
                min_value=0, 
                value=st.session_state["current_inventory"].get(ing, 0), 
                step=1, key=f"inv_{ing}"
            )
    
    st.markdown("---")
    if st.button("✅ 在庫を保存する", key="save_inventory", use_container_width=True):
        try:
            st.session_state["current_inventory"] = current_inventory
            save_inventory_to_csv(current_inventory)
        except Exception as e:
            st.error(f"在庫保存中にエラーが発生しました: {e}")
    
    st.markdown("### 📊 現在の在庫状況")
    df_inventory = pd.DataFrame(list(current_inventory.items()), columns=["ネタ", "在庫枚数"])
    st.table(df_inventory)

# =====================================================
# タブ④：発注計算
# =====================================================
with tab4:
    st.header("④ 発注計算")
    st.markdown("### 明日の必要ネタ数（タブ②）と在庫数（タブ③）を比較し、不足分を発注ロット単位で計算します。")
    
    st.markdown("---")
    if st.button("✅ 発注を計算する", key="calc_order", use_container_width=True):
        try:
            if "tomorrow_required" in st.session_state and st.session_state["tomorrow_required"]:
                tomorrow_required = st.session_state["tomorrow_required"]
                current_inventory = st.session_state["current_inventory"]
                order_calculation = []
                total_order_items = 0
                
                for ing in ingredients:
                    required = tomorrow_required.get(ing, 0)
                    inventory = current_inventory.get(ing, 0)
                    shortage = max(0, required - inventory)
                    lot = order_lot.get(ing, 1)
                    order_qty = math.ceil(shortage / lot) * lot if shortage > 0 else 0
                    if order_qty > 0:
                        total_order_items += 1
                    order_calculation.append({
                        "ネタ": ing,
                        "必要枚数": required,
                        "在庫": inventory,
                        "不足枚数": shortage,
                        "発注ロット": lot,
                        "発注数量": order_qty
                    })
                
                st.markdown("### 📋 発注計算結果")
                df_order = pd.DataFrame(order_calculation)
                st.table(df_order)
                
                st.markdown("### 📦 発注サマリー")
                if total_order_items > 0:
                    st.info(f"合計 {total_order_items} 種類のネタを発注する必要があります。")
                    csv = df_order.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 発注リストをCSVでダウンロード",
                        data=csv,
                        file_name=f"発注リスト_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv", use_container_width=True
                    )
                    st.success("タブ⑤の印刷用レポートからも印刷できます。")
                else:
                    st.success("✅ すべてのネタが在庫で足りています。発注は不要です。")
                
                st.session_state["order_calculation"] = order_calculation
            else:
                st.info("まずはタブ②（明日の製造計画）とタブ③（在庫入力）を実施してください。")
                st.markdown("""
                ### 📝 手順ガイド
                1. 「② 明日の製造計画」タブで明日の製造目標を入力
                2. 「③ 在庫入力」タブで現在の在庫数を入力
                3. このタブに戻り「発注を計算する」ボタンを押す
                """)
        except Exception as e:
            st.error(f"発注計算中にエラーが発生しました: {e}")

# =====================================================
# タブ⑤：印刷用レポート（エクスポート強化：CSV, Excel, PDF）
# =====================================================
with tab5:
    st.header("⑤ 印刷用レポート")
    st.markdown("### 計算結果を印刷するためのレポートを表示します。")
    
    report_type = st.radio(
        "表示するレポートを選択してください 👇",
        ["今日の製造集計", "明日の製造計画", "発注計算結果"],
        horizontal=True
    )
    
    st.markdown("---")
    if report_type == "今日の製造集計":
        st.markdown("## 📑 今日の製造集計レポート")
        if "today_report" in st.session_state and st.session_state["today_report"]:
            report = st.session_state["today_report"]
            st.markdown(f"### 📅 製造日: {report.get('date', datetime.now().strftime('%Y年%m月%d日'))}")
            
            st.markdown("### 📊 製造セット集計")
            df_today_report = pd.DataFrame(report["summary"])
            st.table(df_today_report)
            st.markdown(f"### 💰 合計製造金額: ¥{report['total_money']:,}")
            st.markdown(f"### 🛒 合計原価: ¥{report['total_cost']:,}")
            st.markdown(f"### 💡 推定利益: ¥{report['total_money'] - report['total_cost']:,}")
            
            st.markdown("### 🔪 使用ネタ集計")
            usage_items = [(ing, qty) for ing, qty in report["usage"].items() if qty > 0]
            if usage_items:
                df_usage_report = pd.DataFrame(usage_items, columns=["ネタ", "使用枚数"])
                st.table(df_usage_report)
            else:
                st.info("使用したネタはありません。")
            
            st.markdown("### 📥 レポートのダウンロード")
            col1, col2, col3 = st.columns(3)
            with col1:
                df_sets = pd.DataFrame(report["summary"])
                csv_sets = df_sets.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 製造集計CSVダウンロード", 
                    csv_sets, 
                    file_name=f"製造集計_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True
                )
            with col2:
                if usage_items:
                    df_usage = pd.DataFrame(usage_items, columns=["ネタ", "使用枚数"])
                    csv_usage = df_usage.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "🔪 使用ネタCSVダウンロード", 
                        csv_usage, 
                        file_name=f"使用ネタ_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv", use_container_width=True
                    )
            with col3:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_sets.to_excel(writer, index=False, sheet_name='製造集計')
                    if usage_items:
                        df_usage.to_excel(writer, index=False, sheet_name='使用ネタ')
                    writer.save()
                st.download_button(
                    "📥 Excelダウンロード", 
                    output.getvalue(), 
                    file_name=f"レポート_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True
                )
            
            st.markdown("### 🖨️ PDFとしてダウンロード")
            if st.button("PDFダウンロード生成", key="pdf_today"):
                report_html = f"""
                <html>
                <head>
                  <meta charset="utf-8">
                  <style>
                    body {{ font-size: 20px; }}
                    table, th, td {{ border: 1px solid black; border-collapse: collapse; padding: 8px; }}
                  </style>
                </head>
                <body>
                  <h1>今日の製造集計レポート</h1>
                  <p>製造日: {report.get('date', datetime.now().strftime('%Y年%m月%d日'))}</p>
                  {df_today_report.to_html(index=False)}
                  <p>合計製造金額: ¥{report['total_money']:,}</p>
                  <p>合計原価: ¥{report['total_cost']:,}</p>
                  <p>推定利益: ¥{report['total_money'] - report['total_cost']:,}</p>
                </body>
                </html>
                """
                try:
                    pdf = pdfkit.from_string(report_html, False)
                    st.download_button(
                        "PDFダウンロード", 
                        pdf, 
                        file_name=f"製造集計_{datetime.now().strftime('%Y%m%d')}.pdf", 
                        mime="application/pdf", use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF生成エラー: {e}")
        else:
            st.error("まだ『今日の製造計画』が計算されていません。")
            
    elif report_type == "明日の製造計画":
        st.markdown("## 📑 明日の製造計画レポート")
        if "tomorrow_summary" in st.session_state and st.session_state["tomorrow_summary"]:
            tomorrow_summary = st.session_state["tomorrow_summary"]
            tomorrow_total = st.session_state["tomorrow_total"]
            tomorrow_required = st.session_state["tomorrow_required"]
            next_date = (datetime.now() + timedelta(days=1)).strftime('%Y年%m月%d日')
            st.markdown(f"### 📅 計画日: {next_date}")
            df_plan = pd.DataFrame(tomorrow_summary)
            st.table(df_plan)
            st.markdown(f"### 💰 合計目標製造金額: ¥{tomorrow_total:,}")
            
            st.markdown("### 🔪 必要ネタ数")
            required_items = [(ing, qty) for ing, qty in tomorrow_required.items() if qty > 0]
            if required_items:
                df_required = pd.DataFrame(required_items, columns=["ネタ", "必要枚数"])
                st.table(df_required)
            else:
                st.info("必要なネタはありません。")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                csv_plan = df_plan.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 製造計画CSVダウンロード", 
                    csv_plan, 
                    file_name=f"製造計画_{next_date}.csv",
                    mime="text/csv", use_container_width=True
                )
            with col2:
                if required_items:
                    df_required = pd.DataFrame(required_items, columns=["ネタ", "必要枚数"])
                    csv_required = df_required.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "🔪 必要ネタCSVダウンロード", 
                        csv_required, 
                        file_name=f"必要ネタ_{next_date}.csv",
                        mime="text/csv", use_container_width=True
                    )
            with col3:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_plan.to_excel(writer, index=False, sheet_name='製造計画')
                    if required_items:
                        df_required.to_excel(writer, index=False, sheet_name='必要ネタ')
                    writer.save()
                st.download_button(
                    "📥 Excelダウンロード", 
                    output.getvalue(), 
                    file_name=f"明日計画_{next_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True
                )
            
            st.markdown("### 🖨️ 印刷方法")
            st.info("1. このページを印刷するには、Ctrl+P (Windows) または ⌘+P (Mac) を押してください。\n2. 印刷設定が表示されたら「印刷」ボタンを押してください。")
        else:
            st.error("まだ『明日の製造計画』が計算されていません。")
            
    else:
        st.markdown("## 📑 発注計算結果レポート")
        if "order_calculation" in st.session_state and st.session_state["order_calculation"]:
            order_calculation = st.session_state["order_calculation"]
            current_date = datetime.now().strftime('%Y年%m月%d日')
            st.markdown(f"### 📅 発注日: {current_date}")
            df_order = pd.DataFrame(order_calculation)
            show_only_orders = st.checkbox("✅ 発注が必要なアイテムのみ表示", value=True)
            st.markdown("### 📋 発注リスト")
            if show_only_orders:
                df_order_filtered = df_order[df_order["発注数量"] > 0]
                if not df_order_filtered.empty:
                    st.table(df_order_filtered)
                else:
                    st.success("✅ 発注が必要なアイテムはありません。すべてのネタが在庫で足りています。")
            else:
                st.table(df_order)
            
            st.markdown("### 📦 発注サマリー")
            total_order_items = len(df_order[df_order["発注数量"] > 0])
            if total_order_items > 0:
                st.info(f"合計 {total_order_items} 種類のネタを発注する必要があります。")
                csv = df_order.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 発注リストをCSVでダウンロード",
                    data=csv,
                    file_name=f"発注リスト_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True
                )
            else:
                st.success("✅ すべてのネタが在庫で足りています。発注は不要です。")
            
            st.markdown("### 🖨️ 印刷方法")
            st.info("1. このページを印刷するには、Ctrl+P (Windows) または ⌘+P (Mac) を押してください。\n2. 印刷設定が表示されたら「印刷」ボタンを押してください。")
        else:
            st.error("まだ『発注計算』が行われていません。")
            st.markdown("""
            ### 📝 手順ガイド
            1. 「② 明日の製造計画」タブで明日の製造目標を入力
            2. 「③ 在庫入力」タブで現在の在庫数を入力 
            3. 「④ 発注計算」タブで「発注を計算する」ボタンを押す
            4. この画面に戻ってきてください
            """)
            
# =====================================================
# タブ⑥：売上予測（高度化：7日平均と直近3日平均を算出）
# =====================================================
with tab6:
    st.header("⑥ 売上予測")
    st.markdown("### 過去7日間の各セットの売上データを入力してください。\n直近の売れ行きも参考に予測します。")
    sales_data = {}
    for set_name in set_recipes.keys():
        st.markdown(f"#### {set_name}")
        sales_data[set_name] = []
        cols = st.columns(7)
        for i in range(7):
            sales = cols[i].number_input(
                f"日{i+1}の売上", min_value=0, value=0, key=f"{set_name}_sales_{i}"
            )
            sales_data[set_name].append(sales)
    if st.button("✅ 売上予測を計算", key="calc_forecast", use_container_width=True):
        try:
            forecast_summary = []
            total_forecast_money = 0
            for set_name, sales_list in sales_data.items():
                avg_7 = sum(sales_list) / 7
                # 直近3日分が入力されていればそちらも計算（不足している場合は7日平均を利用）
                avg_3 = sum(sales_list[-3:]) / 3 if len(sales_list) >= 3 else avg_7
                # シンプルに両者の平均を予測売上数とする
                forecast_sales = round((avg_7 + avg_3) / 2)
                money = forecast_sales * set_prices[set_name]
                total_forecast_money += money
                forecast_summary.append({
                    "セット名": set_name,
                    "7日平均": round(avg_7, 1),
                    "直近3日平均": round(avg_3, 1),
                    "予測売上数": forecast_sales,
                    "販売単価": f"¥{set_prices[set_name]:,}",
                    "予測売上金額": f"¥{money:,}"
                })
            if forecast_summary:
                st.markdown("### 📊 売上予測結果")
                df_forecast = pd.DataFrame(forecast_summary)
                st.table(df_forecast)
                st.markdown(f"### 💰 合計予測売上金額: ¥{total_forecast_money:,}")
            else:
                st.warning("売上データが入力されていません。")
        except Exception as e:
            st.error(f"売上予測計算中にエラーが発生しました: {e}")

# =====================================================
# タブ⑦：原価計算
# =====================================================
with tab7:
    st.header("⑦ 原価計算")
    st.markdown("### 各セットの原価と利益を計算します。")
    try:
        cost_summary = []
        for set_name, recipe in set_recipes.items():
            cost_per_set = sum(recipe[ing] * ingredient_cost[ing] for ing in ingredients)
            price = set_prices[set_name]
            profit = price - cost_per_set
            profit_margin = (profit / price * 100) if price > 0 else 0
            cost_summary.append({
                "セット名": set_name,
                "原価": f"¥{cost_per_set:,}",
                "販売価格": f"¥{price:,}",
                "利益": f"¥{profit:,}",
                "利益率": f"{profit_margin:.1f}%"
            })
        df_cost = pd.DataFrame(cost_summary)
        st.table(df_cost)
        
        st.markdown("### 詳細な原価計算")
        st.markdown("※ 各ネタの原価（単価）:")
        df_ing_cost = pd.DataFrame(list(ingredient_cost.items()), columns=["ネタ", "単価"])
        st.table(df_ing_cost)
    except Exception as e:
        st.error(f"原価計算中にエラーが発生しました: {e}")
