import streamlit as st
from openai import OpenAI
import os

st.set_page_config(page_title="学生 AI 助手", layout="centered")

with st.sidebar:
    st.header("身份验证")
    access_password = st.text_input("请输入访问口令", type="password")
    st.divider()
    st.caption("请输入班级统一口令以开启 AI 助手服务。")

api_key = st.secrets.get("DEEPSEEK_API_KEY")

if not access_password or access_password != "sk-2dd85250bb474026a1592d3dce1d6376":
    st.title("🤖 我的学生 AI 助手")
    st.warning("请在左侧侧边栏输入正确的访问口令以继续。")
    st.stop()

st.title("🤖 我的学生 AI 助手")

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
        st.error("系统配置错误：未检测到后端 API 密钥。")
    else:
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            with st.chat_message("assistant"):
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=st.session_state.messages,
                    stream=False
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error("对话服务暂时不可用，请稍后再试。")
