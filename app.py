from flask import Flask, request, render_template
import google.generativeai as genai
from markdown2 import Markdown
from dotenv import load_dotenv
import os

load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

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




@app.route('/experimental', methods=['GET'])
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



if __name__ == "__main__":
    app.run()