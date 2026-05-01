import streamlit as st
from openai import OpenAI
import os

st.set_page_config(page_title="学生 AI 助手", layout="centered")
st.title("🤖 我的学生 AI 助手")

with st.sidebar:
    st.header("身份验证")
    access_password = st.text_input("请输入访问口令", type="password")
    st.info("请输入班级统一口令以开启 AI 助手服务。")

if access_password != "sk-2dd85250bb474026a1592d3dce1d6376":
    st.warning("口令错误或未输入，请联系管理员获取口令。")
    st.stop()

api_key = os.environ.get("DEEPSEEK_API_KEY")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("同学，有什么我可以帮你的吗？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("后台未配置 API Key，请检查环境变量设置。")
    else:
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

            with st.chat_message("assistant"):
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=st.session_state.messages
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"对话请求失败，请稍后重试。")
