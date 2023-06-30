from flask import Flask, request, abort
import re
import datetime
import os
import time
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


load_dotenv()


app = Flask(__name__)


access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(access_token)
handler = WebhookHandler(channel_secret)


# ロボ娘を起動する関数
def boot_robot():
    print("ロボ娘起動、起きろーー!!(spresenseにHTTP通信を送る)\n")


@app.route("/")
def test():
    print("python request きちゃ")
    return "OK"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Please check your channel access token/channel secret")
        abort(400)

    return 'OK'


users = {}


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    pattern = r"(\d+)時(\d+)分"

    # リッチメニュー「アラーム設定」ボタンを押したときの処理
    if event.message.text == "アラームを設定":
        reply_text = "何時に設定する？"

    # 送られてきたメッセージが「〇〇時〇〇分」の形式かどうかを判定
    elif re.search(pattern, event.message.text):
        match = re.search(pattern, event.message.text)

        hour = match.group(1)
        minute = match.group(2)

        dt_now = datetime.datetime.now()
        start_sec = dt_now.hour*3600 + dt_now.minute*60 + dt_now.second
        end_sec = int(hour)*3600 + int(minute)*60
        dif = abs(end_sec - start_sec)
        reply_text = "{}時{}分に設定したよ.{}秒後に起きればいいってことだ".format(hour, minute, dif)

    else:
        reply_text = event.message.text

    # ineにメッセージを送る
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text))
    # 目的の時間までの秒数をカウント
    time.sleep(dif)
    # ロボ娘起動
    boot_robot()


if __name__ == "__main__":
    app.run()
