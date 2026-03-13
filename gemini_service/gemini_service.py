import os
import requests
import base64
from datetime import datetime

# ---------------------------------------
# Pollinations Image API (Stable)
# ---------------------------------------
POLLINATIONS_URL = "https://pollinations.ai/p/generate"

GENERATED_DIR = "generated"
os.makedirs(GENERATED_DIR, exist_ok=True)

# ---------------------------------------
# Typos detection & auto-fix for "generate"
# ---------------------------------------
def is_image_request(text: str):
    text = text.lower().strip()

    image_words = [
        "generate image",
        "create image",
        "make image",
        "image of",
        "picture of",
        "photo of",
        "img of",
        "draw",
        "render"
    ]

    generate_typos = [
        "genarate", "genrate", "geanrate", "ganerate",
        "generat", "genarte", "ginerate", "geenrate",
        "geneerate", "gnenerate", "genreate", "genetrate"
    ]

    # direct matches
    if any(w in text for w in image_words):
        return True

    # typo + contains word "image"
    if "image" in text:
        for typo in generate_typos:
            if typo in text:
                return True

    # short weird typos
    if text.startswith(("gen", "ge", "ga", "gi")) and "image" in text:
        return True

    return False


# ---------------------------------------
# Prompt Sanitizer
# ---------------------------------------
def sanitize_prompt(prompt: str):
    p = prompt.lower().strip()

    # Repair "cute cat" block
    if "cute cat" in p:
        return "an adorable fluffy adult cat, digital art, ultra-detailed"

    # Block real persons automatically
    real_people = ["virat", "kohli", "modi", "salman", "elon", "srk", "shahrukh"]
    if any(name in p for name in real_people):
        return "a fictional person playing sports, high quality digital art"

    # Short prompts → expand automatically
    if len(prompt.split()) <= 3:
        return prompt + ", digital art, high detail, 4k"

    return prompt


# ---------------------------------------
# Text Generation (Gemini)
# ---------------------------------------
try:
    import google.generativeai as genai
    genai.configure(api_key="AIzaSyBSqdT0H_niDg9oS6yNqgoDQIoxwaJtak0")
    TEXT_MODEL = genai.GenerativeModel("gemini-2.0-flash")
except:
    TEXT_MODEL = None


def generate_text(prompt: str):
    if not TEXT_MODEL:
        return "Gemini not available."
    try:
        resp = TEXT_MODEL.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"[TEXT ERROR] {str(e)}"


# ---------------------------------------
# Pollinations Image Generation
# ---------------------------------------
def generate_image(prompt: str):
    prompt = sanitize_prompt(prompt)

    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}"
        r = requests.get(url)

        if r.status_code != 200:
            return None

        fname = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(GENERATED_DIR, fname)

        with open(path, "wb") as f:
            f.write(r.content)

        return fname

    except Exception as e:
        print("IMAGE ERROR:", e)
        return None





