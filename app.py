from flask import Flask, request, Response, render_template
import google.generativeai as genai
from markdown2 import Markdown
from dotenv import load_dotenv
import os

from google import genai as genai_new
from google.genai import types
from PIL import Image
from io import BytesIO
# import random
import time

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
    gemini_model = genai.GenerativeModel(gemini_text_model)

    q = request.form.get("q")

    def generate():
        try:
            response = gemini_model.generate_content(q, stream=True)
            # markdowner = Markdown(['nl2br'])
            for chunk in response:
                # formatted_chunk = markdowner.convert(chunk.text)
                text = chunk.text
                formatted_chunk = text.replace("\n", "<br>")
                yield f"{formatted_chunk}"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return Response(generate(), mimetype='text/html')


    # r = gemini_model.generate_content(q, stream=True)
    # markdowner = Markdown()
    # formatted_response = markdowner.convert(r.text)
    
    # return render_template('experimental/gemini_text.html', q=q, r=formatted_response, model=gemini_text_model)


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

if __name__ == "__main__":
    app.run()