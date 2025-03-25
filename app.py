import streamlit as st
import pandas as pd
import math
import io
import base64
from datetime import datetime

# ----------------------------------------
# 初期セット情報（セッション内のみ保持）
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
st.markdown("#### 製造計画の立案・在庫管理・発注計算をサポートします")

# ----------------------------------------
# 発注ロットなどの固定情報
# ----------------------------------------
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
#  (文字大きめ & 印刷時にタブを非表示にしない)
# ----------------------------------------
st.markdown(
    """
    <style>
    /* 画面上のフォントを大きくする */
    .stApp { font-size: 24px; }

    input[type="number"] {
        font-size: 24px !important;
        height: 50px !important;
    }
    .stButton button {
        font-size: 24px !important;
        padding: 15px !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        background-color: #4CAF50 !important;
        color: white !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #ffffff;
        font-size: 24px; /* 表の文字も大きめ */
    }
    th, td {
        border: 2px solid #dddddd;
        text-align: center;
        padding: 15px;
        font-size: 24px;
        color: #000000;
    }
    th {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    tr:nth-child(odd) {
        background-color: #ffffff;
    }
    label {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #333333 !important;
    }
    h1, h2, h3 {
        color: #2E4053 !important;
        font-size: 30px !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        font-size: 24px;
        font-weight: bold;
        background-color: #f0f8ff;
        border-radius: 10px 10px 0 0;
        padding: 10px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .stNumberInput { margin-bottom: 20px; }
    .stAlert {
        font-size: 24px !important;
        padding: 20px !important;
        border-radius: 10px !important;
    }

    /* 印刷時の調整 */
    @media print {
        /* ボタンやフッターなどは非表示（必要に応じて削除OK） */
        .stButton, .stDownloadButton, footer, header {
            display: none !important;
        }
        /* タブは表示したいので非表示にしない */
        body {
            font-size: 28px !important;
        }
        table {
            border: 3px solid black !important;
        }
        th, td {
            border: 2px solid black !important;
            padding: 12px !important;
            font-size: 28px !important;
        }
        /* 背景色をそのまま印刷する設定 */
        * {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------
# セッション状態の初期化
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
# タブの作成
# ----------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, = st.tabs([
    "① 今日の製造計画",
    "② 明日の製造計画",
    "③ 在庫入力",
    "④ 発注計算",
    "⑤ 印刷用レポート",
    "⑥ レシピ・価格カスタマイズ管理",
    
])

##############################################
# タブ①：今日の製造計画
##############################################
with tab1:
    st.header("① 今日の製造計画")
    st.markdown("#### 各セットの製造数を入力し、下の「今日の計画を計算」ボタンを押してください。")

    # st.session_state["sets_data"] を読み込み
    sets_data = st.session_state["sets_data"]

    st.markdown("##### 🔍 セット内容の確認")
    # カスタマイズ済みのセット情報をテーブル表示
    set_info = []
    for set_name, data in sets_data.items():
        price = data["販売価格"]
        recipe = data["レシピ"]
        neta_info = ", ".join([f"{ing}: {cnt}枚" for ing, cnt in recipe.items() if cnt > 0]) or "特別品"
        set_info.append({
            "セット名": set_name,
            "使用ネタ": neta_info,
            "販売価格": f"¥{price:,}"
        })
    df_set_info = pd.DataFrame(set_info)
    st.table(df_set_info)
    
    st.markdown("---")
    st.markdown("##### 📝 製造数の入力")
    col1, col2 = st.columns(2)
    today_plan = {}
    # カスタマイズされたセット順に入力欄を生成
    for i, (set_name, data) in enumerate(sets_data.items()):
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

        # 計算ロジック：sets_dataを参照
        for set_name, count in today_plan.items():
            if count > 0:
                price = sets_data[set_name]["販売価格"]
                recipe = sets_data[set_name]["レシピ"]
                money = count * price
                total_production_money += money
                today_summary.append({
                    "セット名": set_name,
                    "製造数": count,
                    "販売単価": f"¥{price:,}",
                    "製造金額": f"¥{money:,}"
                })
                # ネタ使用数を集計
                for ing, req in recipe.items():
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
    st.markdown("#### 各セットの明日の製造目標数を入力し、下の「明日の計画を計算」ボタンを押してください。")
    
    sets_data = st.session_state["sets_data"]

    st.markdown("##### 🔍 セット内容の確認")
    st.table(df_set_info)  # タブ①と同じ表示用DataFrameを使ってもOK
    
    st.markdown("---")
    st.markdown("##### 📝 製造目標数の入力")
    col1, col2 = st.columns(2)
    tomorrow_plan = {}
    # カスタマイズされたセット順に入力欄を生成
    for i, (set_name, data) in enumerate(sets_data.items()):
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
                price = sets_data[set_name]["販売価格"]
                recipe = sets_data[set_name]["レシピ"]
                money = count * price
                total_target_money += money
                tomorrow_summary.append({
                    "セット名": set_name,
                    "製造目標数": count,
                    "販売単価": f"¥{price:,}",
                    "目標製造金額": f"¥{money:,}"
                })
                # 必要ネタ数を集計
                for ing, req in recipe.items():
                    ingredient_required[ing] += req * count

        if tomorrow_summary:
            st.markdown("### 📊 明日の製造目標")
            df_tomorrow = pd.DataFrame(tomorrow_summary)
            st.table(df_tomorrow)
            st.markdown(f"### 💰 合計目標製造金額: ¥{total_target_money:,}")
            
            st.markdown("### 🔪 明日の必要ネタ数")
            required_data = [(ing, c) for ing, c in ingredient_required.items() if c > 0]
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
    st.markdown("#### 現在の各ネタの在庫数を入力してください。（アプリ再起動でリセットされます）")
    
    st.markdown("##### 📝 在庫枚数の入力")
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
    st.markdown("#### 明日の必要ネタ数(タブ②)と在庫数(タブ③)を比較し、不足分を発注ロット単位で計算します。")
    
    st.markdown("---")
    if st.button("✅ 発注を計算する", key="calc_order", use_container_width=True):
        if st.session_state.get("tomorrow_required"):
            tomorrow_required = st.session_state["tomorrow_required"]
            current_inventory = st.session_state["current_inventory"]
            order_calculation = []
            for ing in ingredients:
                required = tomorrow_required.get(ing, 0)
                inventory = current_inventory.get(ing, 0)
                shortage = max(0, required - inventory)
                lot = order_lot.get(ing, 1)
                order_qty = math.ceil(shortage / lot) * lot if shortage > 0 else 0
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
            st.session_state["order_calculation"] = order_calculation
        else:
            st.info("まずは『明日の製造計画』と『在庫入力』を行ってください。")

##############################################
# タブ⑤：印刷用レポート
##############################################
with tab5:
    st.header("⑤ 印刷用レポート")
    print_view_toggle = st.checkbox("🖨️ 印刷ビューに切り替える", value=st.session_state["print_view"])
    st.session_state["print_view"] = print_view_toggle
    
    st.markdown("#### 印刷用レポートを表示します。")
    st.info("**印刷したいタブを選択した状態で、ブラウザの印刷機能(Ctrl+P / ⌘+P)を使ってください。**")

    report_type = st.radio("表示するレポートを選択してください", ["今日の製造集計", "明日の製造計画", "発注計算結果"], horizontal=True)
    st.markdown("---")
    
    if report_type == "今日の製造集計":
        st.markdown("## 📑 今日の製造集計レポート")
        report = st.session_state.get("today_report")
        if report:
            st.markdown(f"### 製造日: {report.get('date', current_date)}")
            st.markdown("### 製造セット集計")
            df_today_report = pd.DataFrame(report["summary"])
            st.table(df_today_report)
            st.markdown(f"### 合計製造金額: ¥{report['total_money']:,}")
            st.markdown("### 使用ネタ集計")
            usage_items = [(ing, qty) for ing, qty in report["usage"].items() if qty > 0]
            if usage_items:
                df_usage_report = pd.DataFrame(usage_items, columns=["ネタ", "使用枚数"])
                st.table(df_usage_report)
            else:
                st.info("使用したネタはありません。")
        else:
            st.error("まだ『今日の製造計画』が計算されていません。")
    
    elif report_type == "明日の製造計画":
        st.markdown("## 📑 明日の製造計画レポート")
        tomorrow_summary = st.session_state.get("tomorrow_summary")
        tomorrow_total = st.session_state.get("tomorrow_total")
        tomorrow_required = st.session_state.get("tomorrow_required")
        if tomorrow_summary:
            next_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                         + pd.Timedelta(days=1)).strftime('%Y年%m月%d日')
            st.markdown(f"### 計画日: {next_date}")
            st.markdown("### 製造セット計画")
            df_plan = pd.DataFrame(tomorrow_summary)
            st.table(df_plan)
            st.markdown(f"### 合計目標製造金額: ¥{tomorrow_total:,}")
            st.markdown("### 必要ネタ数")
            required_items = [(ing, qty) for ing, qty in tomorrow_required.items() if qty > 0]
            if required_items:
                df_required = pd.DataFrame(required_items, columns=["ネタ", "必要枚数"])
                st.table(df_required)
            else:
                st.info("必要なネタはありません。")
        else:
            st.error("まだ『明日の製造計画』が計算されていません。")
    
    else:
        st.markdown("## 📑 発注計算結果レポート")
        order_calculation = st.session_state.get("order_calculation")
        if order_calculation:
            current_date_report = datetime.now().strftime('%Y年%m月%d日')
            st.markdown(f"### 発注日: {current_date_report}")
            df_order = pd.DataFrame(order_calculation)
            st.markdown("### 発注リスト")
            st.table(df_order)
        else:
            st.error("まだ『発注計算』が行われていません。")


##############################################
# タブ⑥：レシピ・価格カスタマイズ管理（セッション内のみ）
##############################################
with tab6:
    st.header("⑥ レシピ・価格カスタマイズ管理")
    st.markdown("#### セットごとのレシピや販売価格、ステータスを自由に変更・登録できます。（データはセッション内のみ保持）")
    
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
    
    # セット選択または新規追加の選択
    set_operation = st.radio("操作を選択", ["新規セット追加", "既存セット編集"])
    
    if set_operation == "既存セット編集":
        edit_set_name = st.selectbox("編集するセット名", list(sets_data.keys()))
        default_price = sets_data[edit_set_name]["販売価格"]
        default_status = sets_data[edit_set_name]["ステータス"]
        default_recipe = sets_data[edit_set_name]["レシピ"]
    else:
        edit_set_name = st.text_input("新規セット名", "")
        default_price = 0
        default_status = "通常"
        default_recipe = {ing: 0 for ing in ingredients}
    
    price_input = st.number_input("販売価格", min_value=0, value=default_price, step=10)
    status_input = st.selectbox("ステータス", ["通常", "広告品", "特売", "イベント"], index=["通常", "広告品", "特売", "イベント"].index(default_status))
    
    recipe_input = {}
    for ing in ingredients:
        recipe_input[ing] = st.number_input(f"{ing} の使用枚数", min_value=0, value=default_recipe.get(ing, 0), step=1)
    
    if st.button("セット情報を保存"):
        if edit_set_name:
            sets_data[edit_set_name] = {
                "レシピ": recipe_input,
                "販売価格": price_input,
                "ステータス": status_input
            }
            st.session_state["sets_data"] = sets_data
            st.success(f"『{edit_set_name}』のセット情報が保存されました！")
            
            # セット情報の再表示のため画面をリロード
            st.experimental_rerun()
        else:
            st.error("セット名を入力してください。")
