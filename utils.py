import os
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 API 키를 가져옵니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API 키가 없는 경우, 사용자에게 명확한 오류 메시지를 제공합니다.
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API 키가 필요합니다. .env 파일에 OPENAI_API_KEY='your_api_key' 형식으로 키를 추가해주세요.")

# OpenAI 클라이언트를 초기화합니다. async_client는 비동기 호출에 사용되고, sync_client는 동기 호출에 사용됩니다.
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
)
sync_client = OpenAI(
    api_key=OPENAI_API_KEY,
)

def llm_call(prompt: str,  model: str = "gpt-4o-mini") -> str:
    messages = []
    messages.append({"role": "user", "content": prompt})
    chat_completion = sync_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return chat_completion.choices[0].message.content


async def llm_call_async(prompt: str,  model: str = "gpt-4o-mini") -> str:
    messages = []
    messages.append({"role": "user", "content": prompt})
    chat_completion = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    print(model,"완료")
    
    return chat_completion.choices[0].message.content


if __name__ == "__main__":
    test = llm_call("안녕")
    print(test)
