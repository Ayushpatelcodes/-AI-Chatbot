# api_server.py
"""
API server for Baderia AI Assistant
- Uses gemini_service for text & image generation (typo-tolerant + sanitizer)
- ML intent model for college FAQ
- Wikipedia fallback
- Endpoints:
    POST /predict   -> expects JSON {"text": "..."}
    POST /generate_image -> expects JSON {"prompt": "..."}
"""

from flask import Flask, request, jsonify
import pickle, json, os, traceback
import wikipediaapi

# Import gemini image/text helpers (must exist)
try:
    from gemini_service.gemini_service import (
        generate_text,
        generate_image,
        is_image_request,
        sanitize_prompt,
    )
except Exception as e:
    # Fallback stubs
    print("Could not import gemini_service:", e)
    def generate_text(p): return "Gemini service not available."
    def generate_image(p): return None
    def is_image_request(p): return False
    def sanitize_prompt(p): return p

# ---------- Load ML model + vectorizer ----------
clf = None
vectorizer = None
INTENT_RESPONSES = {}
MODEL_EXISTS = False

try:
    with open("model/intent_model.pkl", "rb") as f:
        clf = pickle.load(f)
    with open("model/vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open("data/college_faq.json", "r", encoding="utf-8") as f:
        intents_data = json.load(f)
    INTENT_RESPONSES = {item["tag"]: item["responses"] for item in intents_data["intents"]}
    MODEL_EXISTS = True
except Exception as e:
    print("ML model load warning:", e)
    MODEL_EXISTS = False

# ---------- Wikipedia ----------
wiki = wikipediaapi.Wikipedia(language="en", user_agent="BaderiaAI/1.0")

GK_WORDS = [
    "who is", "what is", "when", "where", "why", "how",
    "minister", "president", "pm", "prime minister",
    "formula", "math", "science", "india"
]

def is_gk(text: str):
    t = text.lower()
    return any(w in t for w in GK_WORDS)

def wikipedia_answer(q: str):
    try:
        page = wiki.page(q)
        if page.exists():
            return page.summary[:500]
        return None
    except Exception:
        return None

# ---------- ML intent prediction ----------
from sklearn.exceptions import NotFittedError

def predict_intent(text: str):
    if not MODEL_EXISTS or vectorizer is None or clf is None:
        raise RuntimeError("ML model not available")
    try:
        X = vectorizer.transform([text])
        tag = clf.predict(X)[0]
        prob = max(clf.predict_proba(X)[0])
        return tag, prob
    except NotFittedError:
        raise
    except Exception as e:
        print("Intent prediction error:", e)
        raise

# ---------- Flask app ----------
app = Flask(__name__)

@app.post("/predict")
def predict():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"tag": "error", "responses": ["Please provide text."]}), 400

    # 1) Is it an image request? (typo-tolerant)
    try:
        if is_image_request(text):
            # extract prompt after the first word that indicates image request
            # e.g. "genarate image of cute cat" -> "image of cute cat" -> we want the meaningful part
            # simple heuristic: remove the first token if it is the generate-like token
            parts = text.split(" ", 1)
            prompt_part = parts[1] if len(parts) > 1 else text
            safe_prompt = sanitize_prompt(prompt_part)
            fname = generate_image(safe_prompt)
            if fname:
                return jsonify({"tag": "image", "responses": ["Image generated."], "image": fname})
            else:
                return jsonify({"tag": "error", "responses": ["Image generation failed."]}), 500
    except Exception as e:
        print("Image flow exception:", e)
        traceback.print_exc()

    # 2) General knowledge (Wikipedia then Gemini)
    try:
        if is_gk(text):
            w = wikipedia_answer(text)
            if w:
                return jsonify({"tag": "wikipedia", "responses": [w]})
            # fallback to Gemini text
            g = generate_text(f"Answer in 3-4 lines: {text}")
            if g:
                return jsonify({"tag": "gemini", "responses": [g]})
    except Exception as e:
        print("GK flow error:", e)

    # 3) ML intent model (FAQ)
    if MODEL_EXISTS:
        try:
            tag, prob = predict_intent(text)
            if prob >= 0.55:
                return jsonify({"tag": tag, "responses": INTENT_RESPONSES.get(tag, ["I don't know this yet."])})
        except NotFittedError:
            # model not fitted properly: continue to fallbacks
            print("Model NotFittedError - skipping ML intent step.")
        except Exception as e:
            print("predict_intent error:", e)

    # 4) Wikipedia fallback
    try:
        wf = wikipedia_answer(text)
        if wf:
            return jsonify({"tag": "wikipedia", "responses": [wf]})
    except Exception:
        pass

    # 5) Gemini fallback
    try:
        gf = generate_text(f"Explain shortly: {text}")
        if gf:
            return jsonify({"tag": "gemini", "responses": [gf]})
    except Exception as e:
        print("Gemini fallback error:", e)

    # 6) Unknown
    return jsonify({"tag": "unknown", "responses": ["I don't know this yet."]})

@app.post("/generate_image")
def manual_image():
    data = request.get_json(force=True, silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "No prompt"}), 400
    safe = sanitize_prompt(prompt)
    fname = generate_image(safe)
    if fname:
        return jsonify({"image": fname})
    return jsonify({"error": "Image generation failed"}), 500

# Health
@app.get("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("🔥 API Server running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000)





