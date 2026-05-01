import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from openai import OpenAI

# 1. 建立 Google Sheets 连接
# 注意：请确保在 Streamlit Cloud 的 Secrets 中配置了 [connections.gsheets]
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    # 读取指定的工作表，ttl=0 确保获取的是实时数据而非缓存
    return conn.read(worksheet=worksheet_name, ttl="0")

def update_sheets(worksheet_name, df):
    # 将完整的 DataFrame 覆盖回 Google Sheets
    conn.update(worksheet=worksheet_name, data=df)

# --- 页面配置与样式 ---
st.set_page_config(page_title="研究生 AI 助手中心", layout="wide")

# 隐藏右上角 GitHub 图标和部署按钮，保留三点菜单
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: visible;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stAppDeployButton {display:none;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'login_status' not in st.session_state:
    st.session_state.login_status = False
    st.session_state.user_info = None

# --- 登录与申请逻辑 ---
if not st.session_state.login_status:
    st.title("🎓 欢迎使用智能教育助手")
    tab1, tab2 = st.tabs(["学生登录", "申请访问"])

    with tab1:
        sid = st.text_input("请输入学号登录")
        if st.button("进入系统"):
            users_df = get_data("users")
            user = users_df[users_df['student_id'].astype(str) == str(sid)]
            if not user.empty:
                if user.iloc[0]['status'] == 'approved':
                    st.session_state.login_status = True
                    st.session_state.user_info = user.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.warning("您的访问权限尚未通过审批或已被禁用。")
            else:
                st.error("学号不存在，请先申请访问。")

    with tab2:
        new_sid = st.text_input("申请学号")
        new_name = st.text_input("姓名")
        if st.button("提交申请"):
            users_df = get_data("users")
            if str(new_sid) in users_df['student_id'].astype(str).values:
                st.error("该学号已在系统中。")
            else:
                new_row = pd.DataFrame([{"student_id": new_sid, "name": new_name, "status": "pending", "role": "user"}])
                updated_df = pd.concat([users_df, new_row], ignore_index=True)
                update_sheets("users", updated_df)
                st.success("申请已提交，请等待管理员审核。")

# --- 登录后的主体逻辑 ---
else:
    user = st.session_state.user_info
    st.sidebar.title(f"欢迎, {user['name']}")

    # 动态菜单
    if user['role'] == 'admin':
        menu = st.sidebar.radio("管理菜单", ["待处理申请", "已通过学生管理", "系统参数配置", "AI 对话助手"])
    else:
        menu = "AI 对话助手"

    # 1. 待处理申请管理
    if menu == "待处理申请":
        st.header("⏳ 待处理申请管理")
        users_df = get_data("users")
        pending_users = users_df[(users_df['status'] == 'pending') & (users_df['role'] == 'user')]

        if pending_users.empty:
            st.info("暂无待处理申请。")
        else:
            for index, row in pending_users.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"学号: {row['student_id']} | 姓名: {row['name']}")
                if col2.button("通过", key=f"app_{row['student_id']}"):
                    users_df.loc[users_df['student_id'] == row['student_id'], 'status'] = 'approved'
                    update_sheets("users", users_df)
                    st.rerun()
                if col3.button("驳回", key=f"rej_{row['student_id']}"):
                    users_df.loc[users_df['student_id'] == row['student_id'], 'status'] = 'rejected'
                    update_sheets("users", users_df)
                    st.rerun()

    # 2. 已通过学生管理
    elif menu == "已通过学生管理":
        st.header("👥 已通过学生名单")
        users_df = get_data("users")
        all_approved = users_df[(users_df['status'] == 'approved') & (users_df['role'] == 'user')]

        search_query = st.text_input("搜索学生姓名或学号")
        if not all_approved.empty:
            if search_query:
                all_approved = all_approved[
                    all_approved['name'].astype(str).str.contains(search_query) |
                    all_approved['student_id'].astype(str).str.contains(search_query)
                ]

            st.write(f"当前共有 {len(all_approved)} 名学生拥有访问权限")
            selected_ids = []
            for index, row in all_approved.iterrows():
                if st.checkbox(f"{row['name']} ({row['student_id']})", key=f"select_{row['student_id']}"):
                    selected_ids.append(row['student_id'])

            if selected_ids:
                if st.button("批量取消访问权限", type="primary"):
                    users_df.loc[users_df['student_id'].isin(selected_ids), 'status'] = 'rejected'
                    update_sheets("users", users_df)
                    st.success(f"已成功取消 {len(selected_ids)} 名学生的权限")
                    st.rerun()
        else:
            st.info("目前没有已通过的学生。")

    # 3. 系统参数配置
    elif menu == "系统参数配置":
        st.header("⚙️ 系统参数配置")
        settings_df = get_data("settings")
        
        # 获取当前的 API KEY
        current_key = ""
        if not settings_df.empty and "DEEPSEEK_API_KEY" in settings_df['config_key'].values:
            current_key = settings_df.loc[settings_df['config_key'] == "DEEPSEEK_API_KEY", "config_value"].values[0]
        
        new_key = st.text_input("DeepSeek API Key", value=current_key, type="password")
        if st.button("保存配置"):
            if "DEEPSEEK_API_KEY" in settings_df['config_key'].values:
                settings_df.loc[settings_df['config_key'] == "DEEPSEEK_API_KEY", "config_value"] = new_key
            else:
                new_row = pd.DataFrame([{"config_key": "DEEPSEEK_API_KEY", "config_value": new_key}])
                settings_df = pd.concat([settings_df, new_row], ignore_index=True)
            update_sheets("settings", settings_df)
            st.success("API 配置已成功保存到云端表格！")

    # 4. AI 对话助手
    elif menu == "AI 对话助手":
        st.header("🤖 智能学术助手")
        settings_df = get_data("settings")
        api_key = None
        if not settings_df.empty and "DEEPSEEK_API_KEY" in settings_df['config_key'].values:
            api_key = settings_df.loc[settings_df['config_key'] == "DEEPSEEK_API_KEY", "config_value"].values[0]

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("请输入您的问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if not api_key or api_key == "":
                st.error("管理员尚未配置 API Key，请前往‘系统参数配置’进行设置。")
            else:
                try:
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                    with st.chat_message("assistant"):
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=st.session_state.messages,
                            stream=False
                        )
                        ans = response.choices[0].message.content
                        st.markdown(ans)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                except Exception as e:
                    st.error(f"对话失败，请检查 API Key 是否正确或网络是否通畅。错误详情: {e}")

    if st.sidebar.button("退出登录"):
        st.session_state.login_status = False
        st.session_state.messages = [] # 退出时清空对话记录
        st.rerun()
