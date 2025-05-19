from flask import Flask, request, render_template
import google.generativeai as genai
from markdown2 import Markdown
from dotenv import load_dotenv
load_dotenv()
import os

from google import genai as genai_new
from google.genai import types

from PIL import Image
from io import BytesIO
import time
import requests
from datetime import datetime

# Gemini Telegram chat
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
client = genai_new.Client(api_key=GEMINI_API_KEY)
url = f'https://api.telegram.org/bot{TELEGRAM_API_KEY}/'


app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route('/gemini', methods=["GET", "POST"])
def gemini():
    return render_template("gemini.html")

@app.route('/gemini_reply', methods=["POST"])
def gemini_reply():
    q = request.form.get("q")

    r = model.generate_content(q)

    markdowner = Markdown()
    formatted_response = markdowner.convert(r.text)

    return render_template("gemini_reply.html", r=formatted_response)




@app.route('/experimental/gemini_text', methods=['GET'])
def experimental():
    return render_template('experimental/gemini_text.html')

@app.route('/experimental/gemini_text', methods=['POST'])
def gemini_text():

    gemini_text_model = request.form.get("model")
    genai.GenerativeModel(gemini_text_model)

    q = request.form.get("q")

    r = model.generate_content(q)

    markdowner = Markdown()
    formatted_response = markdowner.convert(r.text)
    
    return render_template('experimental/gemini_text.html', q=q, r=formatted_response, model=gemini_text_model)


@app.route('/experimental/gemini_image', methods=['GET'])
def gemini_image():
    return render_template('experimental/gemini_image.html')

@app.route('/experimental/gemini_image/output', methods=['POST'])
def gemini_image_output():
    client = genai_new.Client(api_key=gemini_api_key)

    contents = request.form.get('prompt')

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
        )
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            
            # number = random.randint(0, 999999)
            filename = f"image_{time.time()}.png"
            filepath = f'./static/{filename}'
            image.save(filepath)
            # image.show()

    return render_template('experimental/gemini_image.html', prompt=contents, image=filename)



@app.route('/experimental/telegram/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()  # Parse JSON payload
    message = data.get('message')
    
    chat_id = message['chat']['id']
    message_text = message.get('text', '')

    if message_text.lower() == '/start':
        requests.get(url + f'sendMessage?chat_id={chat_id}&text={"Ask me a question: (or type quit)"}')
        return 'OK', 200
    elif message_text.lower() == "/quit":
        requests.get(url + f'sendMessage?chat_id={chat_id}&text=Good%20Bye!')
        return 'OK', 200
    else:
        # trigger Gemini API
        gemini_result = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction="Use fewer than 101 words in all replies.."),
            contents=[message_text]
        )

        # show "typing..."
        send_action = url + f'sendChatAction?chat_id={chat_id}&action=typing'
        requests.get(send_action)

        r = gemini_result.text
        send_url = url + f'sendMessage?parse_mode=markdown&chat_id={chat_id}&text={r}'
        requests.get(send_url)

        return 'OK', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0')
    # app.run()