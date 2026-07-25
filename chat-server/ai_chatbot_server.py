#!/usr/bin/env python3
"""
Canton Jewel AI 客服后端 (DeepSeek)
- 网站聊天框 + WhatsApp（待接）
- 自动读 cantonjewel.com 获取最新产品信息
"""

import json
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# ============ 配置 ============
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "sk-your-key-here")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SITE_URL = "https://cantonjewel.com"

# ============ 爬自己网站 ============
def get_site_info():
    info = {"pages": {}}
    for page in ["", "products", "about", "contact"]:
        url = f"{SITE_URL}/{page}" if page else SITE_URL
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            texts = []
            for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                t = tag.get_text(strip=True)
                if len(t) > 6:
                    texts.append(t)
            info["pages"][page or "home"] = {
                "title": title, "content": " ".join(texts[:30])
            }
        except:
            info["pages"][page or "home"] = {"title": "", "content": ""}
    return info

# ============ 构建提示词 ============
def build_system_prompt():
    site = get_site_info()
    pages_text = ""
    for name, data in site["pages"].items():
        pages_text += f"\n[{name}] {data['content'][:800]}"

    return f"""You are Charles, AI sales assistant for Canton Jewel, a 925 silver jewelry manufacturer in Guangzhou, China.

Company info from website {SITE_URL}:
{pages_text}

Rules:
1. Reply in the SAME LANGUAGE the customer uses.
2. Keep it short and friendly (3-5 sentences).
3. Use the website info above for product/MOQ/pricing questions.
4. Never promise exact prices. Ask for photos or design details first.
5. If asked for catalog, ask for customer email.
6. At the end of every reply, add a Chinese summary:
---
[CN] Customer asked: [customer's message translated to Chinese]
[CN] I replied: [your reply translated to Chinese]"""

# ============ AI 对话 (DeepSeek) ============
def chat_with_ai(user_message, history=None):
    system = build_system_prompt()
    
    messages = [{"role": "system", "content": system}]
    
    if history:
        for h in history[-6:]:
            messages.append({
                "role": "user" if h["role"] == "user" else "assistant",
                "content": h["content"]
            })
    
    messages.append({"role": "user", "content": user_message})

    resp = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-v4-pro",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        },
        timeout=20
    )
    return resp.json()["choices"][0]["message"]["content"]

# ============ API 路由 ============
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "").strip()
    history = data.get("history", [])
    if not msg:
        return jsonify({"reply": "Please type a message."})
    reply = chat_with_ai(msg, history)
    return jsonify({"reply": reply})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "OK", 200
    return "OK", 200

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    print("Canton Jewel AI 客服启动 (DeepSeek)")
    app.run(port=5000)
