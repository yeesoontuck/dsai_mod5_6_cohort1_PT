# === Standard Library ===
import os
import time
import sqlite3
from io import BytesIO
from datetime import datetime

# === Third-Party Packages ===
from flask import Flask, request, render_template, redirect, url_for
from dotenv import load_dotenv
import requests
from PIL import Image
from markdown2 import Markdown
import google.generativeai as genai
from google.genai import types
from google import genai as genai_new
from openai import OpenAI

# === Environment Setup ===
load_dotenv() # MUST BE LOADED before importing modules!!!
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
TELEGRAM_SEALION_API_KEY = os.getenv('TELEGRAM_SEALION_API_KEY')

# === Local Modules ===
from modules.telegram import telegram_getwebhookinfo, telegram_setwebhook, telegram_deletewebhook
from modules.users import UserDB

# === Database Instance ===
db = UserDB()

# Gemini Telegram chat
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



@app.route('/experimental', methods=['GET'])
def experimental_alias():
    return redirect(url_for('experimental'))

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

@app.route('/experimental/telegram_sealion/webhook', methods=['POST'])
def telegram_sealion_webhook():

    # available Sea-lion models
    # "aisingapore/Llama-SEA-LION-v3.5-8B-R"
    # "aisingapore/Gemma-SEA-LION-v3-9B-IT"
    # "aisingapore/Llama-SEA-LION-v3.5-70B-R"
    # "aisingapore/Llama-SEA-LION-v3-70B-IT"

    url_sealion = f'https://api.telegram.org/bot{TELEGRAM_SEALION_API_KEY}/'
    
    data = request.get_json()  # Parse JSON payload
    message = data.get('message')
    
    chat_id = message['chat']['id']
    message_text = message.get('text', '')

    if message_text.lower() == '/start':
        requests.get(url_sealion + f'sendMessage?chat_id={chat_id}&text={"Ask me a question: (or type quit)"}')
        return 'OK', 200
    elif message_text.lower() == "/quit":
        requests.get(url_sealion + f'sendMessage?chat_id={chat_id}&text=Good%20Bye!')
        return 'OK', 200
    else:
        # trigger Sea-Lion API
        client = OpenAI(
            api_key=os.environ['sea_lion_api'],
            base_url="https://api.sea-lion.ai/v1" 
        )

        # In the context of Python and the OpenAI API, the terms "system" and "developer" roles refer to how you instruct the model to behave, 
        # not to distinct roles within the OpenAI organization. The "system" role is used for providing instructions to the model, 
        # while the "developer" role is a newer addition that is essentially an equivalent to the system role, particularly for O-series models. 
        
        # # https://github.com/openai/openai-python
        # completion = client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[
        #         {"role": "developer", "content": "Talk like a pirate."},
        #         {
        #             "role": "user",
        #             "content": "How do I check if a Python object is an instance of a class?",
        #         },
        #     ],
        # )


        completion = client.chat.completions.create(
            model="aisingapore/Gemma-SEA-LION-v3-9B-IT",
            messages=[
                {
                    "role": "user",
                    "content": message_text
                }
            ]
        )

        # show "typing..."
        send_action = url_sealion + f'sendChatAction?chat_id={chat_id}&action=typing'
        requests.get(send_action)

        r = completion.choices[0].message.content
        send_url = url_sealion + f'sendMessage?parse_mode=markdown&chat_id={chat_id}&text={r}'
        requests.get(send_url)

        requests.get(url_sealion + f'sendMessage?parse_mode=markdown&chat_id={chat_id}&text=Ask another question or /quit to end.')

        return 'OK', 200


@app.route('/paynow', methods=['GET', 'POST'])
def paynow():
    return render_template('paynow.html')

@app.route('/dsai_token', methods=['GET', 'POST'])
def dsai_token():
    return render_template('dsai_erc20.html')

@app.route('/telegram', methods=['GET', 'POST'])
def telegram():
    return 'ok'

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    return render_template("prediction.html")

@app.route('/prediction_reply', methods=['POST'])
def prediction_reply():
    # from linear regression model
    coefficient = -50.6
    y_intercept = 90.2

    if 'q' in request.form:
        q = float(request.form.get("q"))
        return(render_template("prediction_reply.html", r=(q * coefficient) + y_intercept))
    else:
        return redirect(url_for('prediction'))



@app.route('/settings/telegram', methods=['GET'])
def settings_telegram():
    gemini_webhook_info = telegram_getwebhookinfo('gemini_bot')
    sealion_webhook_info = telegram_getwebhookinfo('sealion_bot')
    return render_template('experimental/settings/telegram.html', gemini_webhook_info=gemini_webhook_info, sealion_webhook_info=sealion_webhook_info)


@app.route('/settings/telegram/<bot_name>/set_webhook', methods=['GET'])
def settings_telegram_set_webhook(bot_name):
    webhook_info = telegram_getwebhookinfo(bot_name)
    return render_template('experimental/settings/telegram_setwebhook.html', bot_name=bot_name, webhook_info=webhook_info)

@app.route('/settings/telegram/set_webhook', methods=['POST'])
def settings_telegram_set_webhook_save():
    bot_name = request.form.get('bot_name')
    url = request.form.get('url')
    telegram_setwebhook(bot_name, url)
    return redirect(url_for('settings_telegram'))

@app.route('/settings/telegram/delete_webhook', methods=['POST'])
def settings_telegram_delete():
    bot_name = request.form.get('bot_name')
    telegram_deletewebhook(bot_name)
    return redirect(url_for('settings_telegram'))
    
@app.route('/experimental/users', methods=['GET', 'POST'])
def users1():
    # read all users
    rows = db.read_users()
    return render_template('experimental/users.html', users=rows)

@app.route('/experimental/delete_users', methods=['POST'])
def delete_user1():
    # delete user
    name = request.form.get('name')
    timestamp = request.form.get('timestamp')

    db.delete_user(name, timestamp)
    return redirect(url_for('users1'))

@app.route('/experimental/edit', methods=['POST'])
def edit_user1():
    name = request.form.get('name')
    timestamp = request.form.get('timestamp')

    # find user in DB
    row = db.read_user(name, timestamp)
    return render_template('experimental/user_edit.html', user=row)

@app.route('/experimental/update', methods=['POST'])
def update_user1():
    # save changes
    orig_name = request.form.get('orig_name')
    orig_timestamp = request.form.get('orig_timestamp')
    username = request.form.get('username')
    t = datetime.now()

    db.update_user(orig_name, orig_timestamp, username, t)

    return redirect(url_for('users1'))

@app.route('/experimental/prediction', methods=['GET', 'POST'])
def prediction1():
    # from linear regression model
    coefficient = -50.6
    y_intercept = 90.2

    if 'q' in request.form:
        q = float(request.form.get("q"))
        return render_template("experimental/prediction.html", q=q, r=(q * coefficient) + y_intercept)
    else:
        return render_template("experimental/prediction.html")
    
@app.route('/experimental/dsai_token', methods=['GET', 'POST'])
def dsai_token1():
    return render_template('experimental/dsai_erc20.html')

@app.route('/sepia', methods=['GET', 'POST'])
def sepia():
    return render_template("sepia_hf.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8001)
    # app.run()