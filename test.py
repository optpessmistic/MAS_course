import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COZE_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 第一步：发起对话
data = {
    "bot_id": "7512323036159787044",
    "user_id": "123456789",
    "stream": False,
    "additional_messages": [
        {
            "content": "请你介绍一下你自己？",
            "content_type": "text",
            "role": "user",
            "type": "question"
        }
    ]
}

response = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=data)
result = response.json()
conversation_id = result['data']['conversation_id']
id = result['data']['id']
print(result)
print(id)
print(conversation_id)
status = result['data'].get('status', 'unknown')

time.sleep(5)
while status != "completed":

    url = "https://api.coze.cn/v3/chat/retrieve"
    params = {
        "conversation_id": f"{conversation_id}",
        "chat_id": f"{id}"
    }
    headers = {
        "Authorization": "Bearer pat_gxwBcxQF0Q9EficZQ2Vp7QNBWe51IQgsyGR9DaXX9Hw4umWJ0gOha9lUMhM9kVRv",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    status = result['data']['status']
    time.sleep(2)
print(status)
if status == "completed":
    print("对话检索成功")
    url = "https://api.coze.cn/v3/chat/message/list"
    params = {
    "conversation_id": f"{conversation_id}",
    "chat_id": f"{id}"
}
    headers = {
    "Authorization": "Bearer pat_gxwBcxQF0Q9EficZQ2Vp7QNBWe51IQgsyGR9DaXX9Hw4umWJ0gOha9lUMhM9kVRv",
    "Content-Type": "application/json"
}

    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    answer = result['data'][2]['content']
    print(answer)