from flask import Flask, request, render_template, redirect, url_for
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

import sqlite3

# Gemini Telegram chat
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
client = genai_new.Client(api_key=GEMINI_API_KEY)
url = f'https://api.telegram.org/bot{TELEGRAM_API_KEY}/'


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/main", methods=["GET", "POST"])
def main():
    return render_template("main.html")

@app.route('/gemini', methods=["GET", "POST"])
def gemini():
    return render_template("gemini.html.j2")

@app.route('/gemini_reply', methods=["POST"])
def gemini_reply():
    q = request.form.get("q")

    r = model.generate_content(q)

    markdowner = Markdown()
    formatted_response = markdowner.convert(r.text)

    return render_template("gemini_reply.html", r=formatted_response)

@app.route('/sql', methods=['POST'])
def sql():
    # insert the name into database
    username = request.form.get('username')
    t = datetime.now()

    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (name, timestamp) VALUES(?,?)', (username, t))
    conn.commit()
    c.close()
    conn.close()

    return redirect(url_for('users'))


@app.route('/users', methods=['GET', 'POST'])
def users():
    # read all users
    conn = sqlite3.connect('user.db')
    conn.row_factory = sqlite3.Row  # so we can use column names
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users order by timestamp')
    rows = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=rows)

@app.route('/delete_users', methods=['POST'])
def delete_users():
    # delete all rows
    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('DELETE FROM users')
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('users'))

@app.route('/edit', methods=['POST'])
def edit():
    name = request.form.get('name')
    timestamp = request.form.get('timestamp')

    # find user in DB
    conn = sqlite3.connect('user.db')
    conn.row_factory = sqlite3.Row  # so we can use column names
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users where name = ? and timestamp = ? limit 1', (name, timestamp))
    row = cursor.fetchone()
    conn.close()
    return render_template('user_edit.html', user=row)

@app.route('/update', methods=['POST'])
def update():
    # save changes
    orig_name = request.form.get('orig_name')
    orig_timestamp = request.form.get('orig_timestamp')
    username = request.form.get('username')
    t = datetime.now()

    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('UPDATE users SET name = ?, timestamp = ? where name = ? and timestamp = ?', (username, t, orig_name, orig_timestamp))
    conn.commit()
    c.close()
    conn.close()

    return redirect(url_for('users'))


@app.route('/delete', methods=['POST'])
def delete():
    # delete user
    name = request.form.get('name')
    timestamp = request.form.get('timestamp')

    conn = sqlite3.connect('user.db')
    c = conn.cursor()
    c.execute('DELETE FROM users where name = ? and timestamp = ?', (name, timestamp))
    conn.commit()
    c.close()
    conn.close()

    return redirect(url_for('users'))



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
    client = genai_new.Client(api_key=GEMINI_API_KEY)

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

        requests.get(url + f'sendMessage?parse_mode=markdown&chat_id={chat_id}&text=Ask another question or /quit to end.')

        return 'OK', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0')
    # app.run()