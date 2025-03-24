import streamlit as st
import pandas as pd
import math
import io
import base64
from datetime import datetime

# ----------------------------------------
# 初期セット情報（永続化なし：セッション内のみ）
# ----------------------------------------
DEFAULT_SETS = {
    "極上セット": {
        "レシピ": {"マグロ": 3, "サーモン": 2, "イカ": 1, "玉子": 1, "エビ": 2, "ホタテ": 1},
        "販売価格": 1480,
        "ステータス": "通常"
    },
    "季節の彩りセット": {
        "レシピ": {"マグロ": 2, "サーモン": 2, "イカ": 2, "玉子": 1, "エビ": 1, "ホタテ": 1},
        "販売価格": 1280,
        "ステータス": "通常"
    }
}
# セッションにセット情報がなければ初期値をセット
if "sets_data" not in st.session_state:
    st.session_state["sets_data"] = DEFAULT_SETS.copy()

# ----------------------------------------
# ページ全体の設定
# ----------------------------------------
current_date = datetime.now().strftime("%Y年%m月%d日")
st.set_page_config(
    page_title=f"寿司製造管理システム 🍣 - {current_date}",
    page_icon="🍣",
    layout="wide"
)

st.title(f"🍣 寿司製造管理システム - {current_date} の製造計画")
st.markdown("### 製造計画の立案・在庫管理・発注計算をサポートします")

# ----------------------------------------
# 基本データ定義（固定のレシピ・価格・注文ロット）
# ----------------------------------------
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

# ----------------------------------------
# CSSスタイル
# ----------------------------------------
st.markdown(
    """
    <style>
    .stApp { font-size: 20px; }
    input[type="number"] { font-size: 22px !important; height: 50px !important; }
    .stButton button { 
        font-size: 24px !important; 
        padding: 15px !important; 
        border-radius: 10px !important; 
        font-weight: bold !important; 
        background-color: #4CAF50 !important; 
        color: white !important; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #ffffff; }
    th, td { border: 2px solid #dddddd; text-align: center; padding: 15px; font-size: 22px; color: #000000; }
    th { background-color: #4CAF50; color: white; font-weight: bold; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    tr:nth-child(odd) { background-color: #ffffff; }
    label { font-size: 22px !important; font-weight: bold !important; color: #333333 !important; }
    h1, h2, h3 { color: #2E4053 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; white-space: pre-wrap; font-size: 20px; font-weight: bold; 
        background-color: #f0f8ff; border-radius: 10px 10px 0 0; padding: 10px 16px; 
    }
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

# ----------------------------------------
# セッション状態の初期化（各タブ用）
# ----------------------------------------
if 'today_report' not in st.session_state:
    st.session_state['today_report'] = None
if 'tomorrow_required' not in st.session_state:
    st.session_state['tomorrow_required'] = None
if 'tomorrow_summary' not in st.session_state:
    st.session_state['tomorrow_summary'] = None
if 'tomorrow_total' not in st.session_state:
    st.session_state['tomorrow_total'] = None
if 'current_inventory' not in st.session_state:
    st.session_state['current_inventory'] = {ing: 0 for ing in ingredients}
if 'order_calculation' not in st.session_state:
    st.session_state['order_calculation'] = None
if 'print_view' not in st.session_state:
    st.session_state['print_view'] = False

# ----------------------------------------
# タブの作成（タブ⑦：原価計算を追加）
# ----------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "① 今日の製造計画",
    "② 明日の製造計画",
    "③ 在庫入力",
    "④ 発注計算",
    "⑤ 印刷用レポート",
    "⑥ レシピ・価格カスタマイズ管理",
    "⑦ 原価計算"
])

##############################################
# タブ①：今日の製造計画
##############################################
with tab1:
    st.header("① 今日の製造計画")
    st.markdown("### 各セットの製造数を入力し、下の「今日の計画を計算」ボタンを押してください。")
    
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
                min_value=0, 
                value=0, 
                step=1, 
                key=f"today_{set_name}"
            )
    
    st.markdown("---")
    if st.button("✅ 今日の計画を計算", key="calc_today", use_container_width=True):
        today_summary = []
        total_production_money = 0
        ingredient_usage = {ing: 0 for ing in ingredients}
        for set_name, count in today_plan.items():
            if count > 0:
                price = set_prices.get(set_name, 0)
                money = count * price
                total_production_money += money
                today_summary.append({
                    "セット名": set_name,
                    "製造数": count,
                    "販売単価": f"¥{price:,}",
                    "製造金額": f"¥{money:,}"
                })
                for ing, req in set_recipes[set_name].items():
                    ingredient_usage[ing] += req * count
        if today_summary:
            st.markdown("### 📊 今日の製造集計")
            df_today = pd.DataFrame(today_summary)
            st.table(df_today)
            st.markdown(f"### 💰 合計製造金額: ¥{total_production_money:,}")
            
            st.markdown("### 🔪 使用ネタ集計")
            usage_data = [(ing, count) for ing, count in ingredient_usage.items() if count > 0]
            if usage_data:
                df_usage = pd.DataFrame(usage_data, columns=["ネタ", "使用枚数"])
                st.table(df_usage)
            else:
                st.info("使用するネタはありません。")
            
            st.session_state["today_report"] = {
                "date": current_date,
                "summary": today_summary,
                "total_money": total_production_money,
                "usage": ingredient_usage
            }
            st.success("印刷用レポート(タブ⑤)に反映されました。")
        else:
            st.warning("製造数がすべて0でした。数字を入力してください。")

##############################################
# タブ②：明日の製造計画
##############################################
with tab2:
    st.header("② 明日の製造計画")
    st.markdown("### 各セットの明日の製造目標数を入力し、下の「明日の計画を計算」ボタンを押してください。")
    
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
                min_value=0, 
                value=0, 
                step=1, 
                key=f"tomorrow_{set_name}"
            )
    
    st.markdown("---")
    if st.button("✅ 明日の計画を計算", key="calc_tomorrow", use_container_width=True):
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
            st.success("在庫入力(タブ③)・発注計算(タブ④)で使用されます。")
        else:
            st.warning("すべて0でした。数字を入力してください。")

##############################################
# タブ③：在庫入力
##############################################
with tab3:
    st.header("③ 在庫入力")
    st.markdown("### 現在の各ネタの在庫数を入力してください。（アプリ再起動でリセットされます）")
    
    st.markdown("#### 📝 在庫枚数の入力")
    col1, col2 = st.columns(2)
    current_inventory = {}
    for i, ing in enumerate(ingredients):
        with col1 if i % 2 == 0 else col2:
            current_inventory[ing] = st.number_input(
                f"🍣 {ing} の在庫枚数", 
                min_value=0, 
                value=st.session_state["current_inventory"].get(ing, 0), 
                step=1, 
                key=f"inv_{ing}"
            )
    st.markdown("---")
    if st.button("✅ 在庫を保存する", key="save_inventory", use_container_width=True):
        st.session_state["current_inventory"] = current_inventory
        st.success("在庫データを保存しました。")
    st.markdown("### 📊 現在の在庫状況")
    df_inventory = pd.DataFrame(list(current_inventory.items()), columns=["ネタ", "在庫枚数"])
    st.table(df_inventory)

##############################################
# タブ④：発注計算
##############################################
with tab4:
    st.header("④ 発注計算")
    st.markdown("### 明日の必要ネタ数(タブ②)と在庫数(タブ③)を比較し、不足分を発注ロット単位で計算します。")
    
    st.markdown("---")
    if st.button("✅ 発注を計算する", key="calc_order", use_container_width=True):
        if st.session_state.get("tomorrow_required"):
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
                csv_order = df_order.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 発注リストをCSVでダウンロード",
                    data=csv_order,
                    file_name=f"発注リスト_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.success("✅ すべてのネタが在庫で足りています。発注は不要です。")
            st.session_state["order_calculation"] = order_calculation
        else:
            st.info("まずは『明日の製造計画』と『在庫入力』を行ってください。")
            st.markdown("""
            ### 📝 手順ガイド
            1. 「② 明日の製造計画」タブで明日の製造目標を入力する
            2. 「③ 在庫入力」タブで在庫数を入力する
            3. このタブに戻って「発注を計算する」ボタンを押す
            """)

##############################################
# タブ⑤：印刷用レポート
##############################################
with tab5:
    st.header("⑤ 印刷用レポート")
    print_view_toggle = st.checkbox("🖨️ 印刷ビューに切り替える", value=st.session_state["print_view"])
    st.session_state["print_view"] = print_view_toggle
    
    st.markdown("### 印刷用レポートを表示します。必要に応じてブラウザの印刷機能(Ctrl+P / ⌘+P)で出力してください。")
    report_type = st.radio("表示するレポートを選択してください 👇", ["今日の製造集計", "明日の製造計画", "発注計算結果"], horizontal=True)
    st.markdown("---")
    
    # Excelダウンロード用の関数（writer.save() ではなく with 文でクローズ）
    def get_excel_download_link(df, filename):
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        towrite.seek(0)
        b64 = base64.b64encode(towrite.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Excelダウンロード</a>'
        return href

    if report_type == "今日の製造集計":
        st.markdown("## 📑 今日の製造集計レポート")
        report = st.session_state.get("today_report")
        if report:
            st.markdown(f"### 📅 製造日: {report.get('date', current_date)}")
            st.markdown("### 📊 製造セット集計")
            df_today_report = pd.DataFrame(report["summary"])
            st.table(df_today_report)
            st.markdown(f"### 💰 合計製造金額: ¥{report['total_money']:,}")
            st.markdown("### 🔪 使用ネタ集計")
            usage_items = [(ing, qty) for ing, qty in report["usage"].items() if qty > 0]
            if usage_items:
                df_usage_report = pd.DataFrame(usage_items, columns=["ネタ", "使用枚数"])
                st.table(df_usage_report)
            else:
                st.info("使用したネタはありません。")
            st.markdown("### 📥 レポートのダウンロード")
            col1, col2 = st.columns(2)
            with col1:
                csv_sets = df_today_report.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 製造集計CSVダウンロード", 
                    csv_sets, 
                    file_name=f"製造集計_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown(
                    get_excel_download_link(df_today_report, f"製造集計_{datetime.now().strftime('%Y%m%d')}.xlsx"),
                    unsafe_allow_html=True
                )
            with col2:
                if usage_items:
                    df_usage_items = pd.DataFrame(usage_items, columns=["ネタ", "使用枚数"])
                    csv_usage = df_usage_items.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "🔪 使用ネタCSVダウンロード", 
                        csv_usage, 
                        file_name=f"使用ネタ_{datetime.now().strftime('%Y%m%d')}.csv", 
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.markdown(
                        get_excel_download_link(df_usage_items, f"使用ネタ_{datetime.now().strftime('%Y%m%d')}.xlsx"),
                        unsafe_allow_html=True
                    )
            st.markdown("---")
            st.markdown("### 🖨️ 印刷方法")
            st.info("1. このページを印刷するには、キーボードで「Ctrl+P」(Windows) または「⌘+P」(Mac) を押してください。")
        else:
            st.error("まだ『今日の製造計画』が計算されていません。")
            st.markdown("### 📝 手順ガイド: タブ①で計算し、この画面に戻ってください。")
    
    elif report_type == "明日の製造計画":
        st.markdown("## 📑 明日の製造計画レポート")
        tomorrow_summary = st.session_state.get("tomorrow_summary")
        tomorrow_total = st.session_state.get("tomorrow_total")
        tomorrow_required = st.session_state.get("tomorrow_required")
        if tomorrow_summary:
            next_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)).strftime('%Y年%m月%d日')
            st.markdown(f"### 📅 計画日: {next_date}")
            st.markdown("### 📊 製造セット計画")
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
            st.markdown("### 📥 レポートのダウンロード")
            col1, col2 = st.columns(2)
            with col1:
                csv_plan = df_plan.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📊 製造計画CSVダウンロード", 
                    csv_plan, 
                    file_name=f"製造計画_{next_date}.csv", 
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown(
                    get_excel_download_link(df_plan, f"製造計画_{next_date}.xlsx"),
                    unsafe_allow_html=True
                )
            with col2:
                if required_items:
                    csv_required = df_required.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "🔪 必要ネタCSVダウンロード", 
                        csv_required, 
                        file_name=f"必要ネタ_{next_date}.csv", 
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.markdown(
                        get_excel_download_link(df_required, f"必要ネタ_{next_date}.xlsx"),
                        unsafe_allow_html=True
                    )
            st.markdown("---")
            st.markdown("### 🖨️ 印刷方法")
            st.info("1. このページを印刷するには、キーボードで「Ctrl+P」(Windows) または「⌘+P」(Mac) を押してください。")
        else:
            st.error("まだ『明日の製造計画』が計算されていません。")
            st.markdown("### 📝 手順ガイド: タブ②で計算し、この画面に戻ってください。")
    
    else:
        st.markdown("## 📑 発注計算結果レポート")
        order_calculation = st.session_state.get("order_calculation")
        if order_calculation:
            current_date_report = datetime.now().strftime('%Y年%m月%d日')
            st.markdown(f"### 📅 発注日: {current_date_report}")
            df_order = pd.DataFrame(order_calculation)
            show_only_orders = st.checkbox("✅ 発注が必要なアイテムのみ表示", value=True)
            st.markdown("### 📋 発注リスト")
            if show_only_orders:
                df_order_filtered = df_order[df_order["発注数量"] > 0]
                if not df_order_filtered.empty:
                    st.table(df_order_filtered)
                else:
                    st.success("✅ 発注が必要なアイテムはありません。")
            else:
                st.table(df_order)
            st.markdown("### 📦 発注サマリー")
            total_order_items = len(df_order[df_order["発注数量"] > 0])
            if total_order_items > 0:
                st.info(f"合計 {total_order_items} 種類のネタを発注する必要があります。")
                csv_order = df_order.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 発注リストをCSVでダウンロード", 
                    csv_order, 
                    file_name=f"発注リスト_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown(
                    get_excel_download_link(df_order, f"発注リスト_{datetime.now().strftime('%Y%m%d')}.xlsx"),
                    unsafe_allow_html=True
                )
            else:
                st.success("✅ すべてのネタが在庫で足りています。発注は不要です。")
            st.markdown("---")
            st.markdown("### 🖨️ 印刷方法")
            st.info("1. このページを印刷するには、キーボードで「Ctrl+P」(Windows) または「⌘+P」(Mac) を押してください。")
        else:
            st.error("まだ『発注計算』が行われていません。")
            st.markdown("### 📝 手順ガイド: タブ④で計算し、この画面に戻ってください。")

##############################################
# タブ⑥：レシピ・価格カスタマイズ管理（永続化なし）
##############################################
with tab6:
    st.header("⑥ レシピ・価格カスタマイズ管理")
    st.markdown("### セットごとのレシピや販売価格、ステータスを自由に変更・登録できます。（データはセッション内のみ保持され、再起動でリセットされます）")
    
    sets_data = st.session_state["sets_data"]
    
    st.subheader("現在のセット一覧")
    sets_df = pd.DataFrame([
        {
            "セット名": set_name,
            "販売価格": data["販売価格"],
            "ステータス": data["ステータス"],
            "レシピ": ", ".join([f"{k}: {v}" for k, v in data["レシピ"].items() if v > 0])
        }
        for set_name, data in sets_data.items()
    ])
    st.table(sets_df)
    
    st.subheader("セット情報の追加・編集")
    set_name_input = st.text_input("セット名", "")
    price_input = st.number_input("販売価格", min_value=0, value=0, step=10)
    status_input = st.selectbox("ステータス", ["通常", "広告品", "特売", "イベント"])
    recipe_input = {}
    for ing in ["マグロ", "サーモン", "イカ", "玉子", "エビ", "ホタテ"]:
        recipe_input[ing] = st.number_input(f"{ing} の使用枚数", min_value=0, value=0, step=1)
    
    if st.button("セット情報を保存"):
        if set_name_input:
            sets_data[set_name_input] = {
                "レシピ": recipe_input,
                "販売価格": price_input,
                "ステータス": status_input
            }
            st.success(f"『{set_name_input}』のセット情報が保存されました！")
        else:
            st.error("セット名を入力してください。")

##############################################
# タブ⑦：原価計算（タブ⑥のセット情報を参照）
##############################################
with tab7:
    st.header("⑦ 原価計算")
    st.markdown("### タブ⑥でカスタマイズしたセット情報に基づいて、各セットごとの原価を入力してください。")
    sets_data = st.session_state.get("sets_data", DEFAULT_SETS)
    cost_summary = []
    for set_name, data in sets_data.items():
        selling_price = data["販売価格"]
        cost = st.number_input(f"{set_name} の原価（1セットあたり）", min_value=0, value=0, step=10, key=f"cost_{set_name}")
        profit = selling_price - cost
        cost_summary.append({
            "セット名": set_name,
            "原価": f"¥{cost:,}",
            "販売価格": f"¥{selling_price:,}",
            "利益": f"¥{profit:,}"
        })
    df_cost = pd.DataFrame(cost_summary)
    st.table(df_cost)
