import os
import sys
import io
import streamlit as st
# from dotenv import load_dotenv
from openai import OpenAI

# 한글 윈도우 환경에서 이모지 출력 시 발생하는 cp949 인코딩 에러 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')
# .env 파일 읽기
# load_dotenv()

# 1. API 키 설정 및 클라이언트 생성
API_KEY = os.environ.get("OPENAI_API_KEY") 
client = OpenAI(api_key=API_KEY)

# --- Streamlit 웹 UI 구현 ---
st.set_page_config(page_title="OpenAI 챗봇", page_icon="🤖")

st.title("🤖 OpenAI 기반 AI 챗봇")
st.write("궁금한 내용을 아래에 입력해 보세요.")

# 사용자에게 프롬프트 입력 받기
user_prompt = st.text_area("프롬프트 입력:", placeholder="예: AI Agent를 중학생에게 설명해줘", height=100)

# 전송 버튼 클릭 시 동작
if st.button("질문하기"):
    if not user_prompt.strip():
        st.warning("내용을 입력해 주세요!")
    else:
        with st.spinner("OpenAI가 생각하는 중입니다..."):
            try:
                # 3. 응답 생성
                response = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                # 4. 결과 화면에 출력
                st.markdown("### 💡 답변")
                st.write(response.choices[0].message.content)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
