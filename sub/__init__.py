from os import environ
from typing import Dict
import re
import datetime
import time

from dotenv import load_dotenv
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, Source, TextMessage, TextSendMessage

from sub.gpt.client import ChatGPTClient
from sub.gpt.constants import Model, Role
from sub.gpt.message import Message

load_dotenv(".env", verbose=True)

app = Flask(__name__)

if not (access_token := environ.get("LINE_CHANNEL_ACCESS_TOKEN")):
    raise Exception("access token is not set as an environment variable")

if not (channel_secret := environ.get("LINE_CHANNEL_SECRET")):
    raise Exception("channel secret is not set as an environment variable")

line_bot_api = LineBotApi(access_token)
handler = WebhookHandler(channel_secret)

chatgpt_instance_map: Dict[str, ChatGPTClient] = {}

@app.route('/')
def index():
    return 'Hello, World!'

@app.route("/callback", methods=["POST"])
def callback() -> str:
    signature = request.headers["X-Line-Signature"]

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent) -> None:
    text_message: TextMessage = event.message
    source: Source = event.source
    user_id: str = source.user_id

    pattern = r"(\d+)時(\d+)分"
    flag = False
    
    if text_message.text == "アラームを設定":
        reply_text = "何時に設定する？"

    elif re.search(pattern, event.message.text):
        match = re.search(pattern, event.message.text)

        hour = match.group(1)
        minute = match.group(2)

        dt_now = datetime.datetime.now()
        start_sec = dt_now.hour*3600 + dt_now.minute*60 + dt_now.second
        end_sec = int(hour)*3600 + int(minute)*60
        dif = abs(end_sec - start_sec)
        reply_text = "{}時{}分に設定したわよ.{}秒後に起きればいいってことよ".format(hour, minute, dif)
        flag = True

    else:
        if (gpt_client := chatgpt_instance_map.get(user_id)) is None:
            gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

        gpt_client.add_message(
            message=Message(role=Role.USER, content=f"20文字以内でツンデレの口調で答えて。{text_message.text}")
        )
        res = gpt_client.create()
        chatgpt_instance_map[user_id] = gpt_client

        res_text: str = res["choices"][0]["message"]["content"]
        print(res)

        reply_text = res_text.strip()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

    if flag:
        # 目的の時間までの秒数をカウント
        time.sleep(dif)
        # ロボ娘起動
        print("ロボ娘起動、起きろーー!!(spresenseにHTTP通信を送る)\n")
        flag = False