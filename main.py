import streamlit as st
import sqlite3
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from openai import OpenAI


def get_db_connection():
    return sqlite3.connect('users_data.db', check_same_thread=False)


def get_user(student_id):
    conn = get_db_connection()
    user = pd.read_sql(f"SELECT * FROM users WHERE student_id='{student_id}'", conn)
    conn.close()
    return user


def get_config(key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT config_value FROM settings WHERE config_key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def save_config(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (config_key, config_value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


st.set_page_config(page_title="研究生 AI 助手中心", layout="wide")

# 深度清理界面：隐藏菜单、页眉、页脚及所有 Streamlit 官方浮窗
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    /* 针对移动端的额外隐藏 */
    [data-testid="stStatusWidget"] {display:none;}
    .viewerBadge_container__1QSob {display:none;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

if 'login_status' not in st.session_state:
    st.session_state.login_status = False
    st.session_state.user_info = None

if not st.session_state.login_status:
    st.title("🎓 欢迎使用智能教育助手")
    tab1, tab2 = st.tabs(["学生登录", "申请访问"])

    with tab1:
        sid = st.text_input("请输入学号登录")
        if st.button("进入系统"):
            user = get_user(sid)
            if not user.empty:
                if user.iloc[0]['status'] == 'approved':
                    st.session_state.login_status = True
                    st.session_state.user_info = user.iloc[0]
                    st.rerun()
                else:
                    st.warning("您的访问权限已被禁用或尚未通过审批。")
            else:
                st.error("学号不存在，请先申请访问。")

    with tab2:
        new_sid = st.text_input("申请学号")
        new_name = st.text_input("姓名")
        if st.button("提交申请"):
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO users (student_id, name, status, role) VALUES (?, ?, 'pending', 'user')",
                             (new_sid, new_name))
                conn.commit()
                st.success("申请已提交，请等待管理员审核。")
            except:
                st.error("该学号已在系统中。")
            conn.close()
else:
    user = st.session_state.user_info
    st.sidebar.title(f"欢迎, {user['name']}")

    # 动态菜单
    if user['role'] == 'admin':
        menu = st.sidebar.radio("管理菜单", ["待处理申请", "已通过学生管理", "系统参数配置", "AI 对话助手"])
    else:
        menu = "AI 对话助手"

    # 1. 待处理申请
    if menu == "待处理申请":
        st.header("⏳ 待处理申请管理")
        conn = get_db_connection()
        pending_users = pd.read_sql("SELECT * FROM users WHERE status='pending' AND role='user'", conn)

        if pending_users.empty:
            st.info("暂无待处理申请。")
        else:
            for index, row in pending_users.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"学号: {row['student_id']} | 姓名: {row['name']}")
                if col2.button("通过", key=f"app_{row['student_id']}"):
                    conn.execute("UPDATE users SET status='approved' WHERE student_id=?", (row['student_id'],))
                    conn.commit()
                    st.rerun()
                if col3.button("驳回", key=f"rej_{row['student_id']}"):
                    conn.execute("UPDATE users SET status='rejected' WHERE student_id=?", (row['student_id'],))
                    conn.commit()
                    st.rerun()
        conn.close()

    # 2. 已通过学生管理（新增搜索与多选）
    elif menu == "已通过学生管理":
        st.header("👥 已通过学生名单")
        conn = get_db_connection()

        # 搜索栏
        search_query = st.text_input("搜索学生姓名或学号")
        query = "SELECT student_id, name, status FROM users WHERE status='approved' AND role='user'"
        all_approved = pd.read_sql(query, conn)

        if not all_approved.empty:
            if search_query:
                all_approved = all_approved[
                    all_approved['name'].str.contains(search_query) |
                    all_approved['student_id'].str.contains(search_query)
                    ]

            # 使用 dataframe 结合 checkbox
            st.write(f"当前共有 {len(all_approved)} 名学生拥有访问权限")
            selected_ids = []
            for index, row in all_approved.iterrows():
                if st.checkbox(f"{row['name']} ({row['student_id']})", key=f"select_{row['student_id']}"):
                    selected_ids.append(row['student_id'])

            if selected_ids:
                if st.button("批量取消访问权限", type="primary"):
                    placeholders = ','.join(['?'] * len(selected_ids))
                    conn.execute(f"UPDATE users SET status='rejected' WHERE student_id IN ({placeholders})",
                                 selected_ids)
                    conn.commit()
                    st.success(f"已成功取消 {len(selected_ids)} 名学生的权限")
                    st.rerun()
        else:
            st.info("目前没有已通过的学生。")
        conn.close()

    # 3. 系统参数配置
    elif menu == "系统参数配置":
        st.header("⚙️ 系统参数配置")
        current_key = get_config("DEEPSEEK_API_KEY") or ""
        new_key = st.text_input("DeepSeek API Key", value=current_key, type="password")
        if st.button("保存配置"):
            save_config("DEEPSEEK_API_KEY", new_key)
            st.success("API 配置已成功保存！")

    # 4. AI 对话助手
    elif menu == "AI 对话助手":
        st.header("🤖 智能学术助手")
        api_key = get_config("DEEPSEEK_API_KEY")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("请输入您的问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if not api_key:
                st.error("管理员尚未配置 API Key，请联系管理员。")
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
                    st.error("对话失败，请检查配置或网络状态。")

    if st.sidebar.button("退出登录"):
        st.session_state.login_status = False
        st.rerun()
