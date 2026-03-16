import os, sys

#  PyInstaller OpenCV codec 
if hasattr(sys, '_MEIPASS'):
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ""
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import os, sys

# OpenCV codecs  in PyInstaller
if hasattr(sys, '_MEIPASS'):
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ""

"""
modern_chat_ui1.py — Final corrected FULL VERSION
Includes:
- TRUE FULLSCREEN Splash (Native Tkinter, OpenCV)
- Login, Admin panel, History, Settings
- Pollinations image generation
- Optional Gemini 2.5 fallback
- Intent model fallback
- Math memory
- Voice input
- Defensive UI for CustomTkinter stability
- Embedded Flask backend (/predict)
"""

import os
import sys
import json
import time
import threading
import secrets
import hashlib
import requests
import re
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk

# UI
import customtkinter as ctk
from PIL import Image, ImageTk

# Speech Recognition
try:
    import speech_recognition as sr
    SR_OK = True
except Exception:
    SR_OK = False

# TTS
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
except Exception:
    tts_engine = None

# Flask backend
from flask import Flask, request, jsonify

# Wikipedia
import wikipediaapi

# ML
import pickle
from sklearn.exceptions import NotFittedError

# OpenCV
import cv2

# ----------------------------
# PATHS
# ---------------------------------------------------------------------------
# This section defines all important directory and file locations used by the
# application. These paths allow the program to consistently locate assets,
# store user data, load machine learning models, and save generated images.
# BASE: Root directory of the application.
# ASSETS: Folder containing UI assets such as splash videos.
# USERS_FILE: JSON file where user login credentials are stored.
# HISTORY_DIR: Folder where per-user chat histories are saved.
# MODEL_DIR: Directory that stores trained ML models used for intent detection.
# DATA_DIR: Contains configuration files such as FAQ datasets.
# GENERATED_DIR: Directory where AI‑generated images are stored.
# ---------------------------------------------------------------------------
# ----------------------------
BASE = os.path.abspath(".")
ASSETS = os.path.join(BASE, "assets")
SPLASH_VIDEO = os.path.join(ASSETS, "open.mp4")

USERS_FILE = os.path.join(BASE, "users.json")
HISTORY_DIR = os.path.join(BASE, "history")
MODEL_DIR = os.path.join(BASE, "model")
DATA_DIR = os.path.join(BASE, "data")
GENERATED_DIR = os.path.join(BASE, "generated")

ADMIN_SETUP_KEY = "BADERIA-ADMIN-2025"

os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(ASSETS, exist_ok=True)

# ----------------------------
# Gemini Optional
# ---------------------------------------------------------------------------
# Optional integration with Google Gemini AI model.
# If an API key is provided and the library loads successfully,
# the application can use Gemini as an additional fallback
# to answer user questions when the intent model or Wikipedia
# cannot produce a response.
# ---------------------------------------------------------------------------
# ----------------------------
GEMINI_API_KEY = ""  # input ur api key
USE_GEMINI = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_MODEL = genai.GenerativeModel("gemini-2.5-flash")
        USE_GEMINI = True
        print("Gemini 2.5 loaded")
    except Exception as e:
        print("Gemini init failed:", e)
        USE_GEMINI = False

# ----------------------------
# Password Hash
# ---------------------------------------------------------------------------
# This section implements secure password hashing.
# Instead of storing plain text passwords, the system uses the PBKDF2
# hashing algorithm with SHA‑256 and a randomly generated salt.
# This significantly improves security by preventing password leaks
# if the user database is compromised.
# ---------------------------------------------------------------------------
# ----------------------------
PBKDF_ITER = 200000
HASH_NAME = "sha256"
KEY_LEN = 32

def hash_password(password: str, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(HASH_NAME, password.encode(), salt, PBKDF_ITER, KEY_LEN)
    return {"salt": salt.hex(), "hash": dk.hex()}

def verify_password(stored, password):
    try:
        salt = bytes.fromhex(stored["salt"])
        expected = stored["hash"]
        dk = hashlib.pbkdf2_hmac(HASH_NAME, password.encode(), salt, PBKDF_ITER, KEY_LEN)
        return dk.hex() == expected
    except:
        return False

# ----------------------------
# User DB
# ---------------------------------------------------------------------------
# User database utilities.
# These functions manage the storage and retrieval of user accounts
# and chat histories. Data is stored in JSON format for simplicity.
# Each user has a separate history file so conversations persist
# between sessions.
# ---------------------------------------------------------------------------
# ----------------------------
def ensure_users_db():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)

def load_users():
    ensure_users_db()
    try:
        return json.load(open(USERS_FILE, "r"))
    except:
        return {}

def save_users(u):
    with open(USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)

def history_file(user):
    safe = "".join(c for c in user if c.isalnum() or c in "_-")
    return os.path.join(HISTORY_DIR, f"{safe}.json")

def load_history(user):
    f = history_file(user)
    if os.path.exists(f):
        try:
            return json.load(open(f))
        except:
            return []
    return []

def save_history(user, hist):
    with open(history_file(user), "w") as f:
        json.dump(hist, f, indent=2)

def session_state_file(user):
    safe = "".join(c for c in user if c.isalnum() or c in "_-")
    return os.path.join(HISTORY_DIR, f"{safe}.state.json")

def load_session_state(user):
    f = session_state_file(user)
    if os.path.exists(f):
        try:
            return json.load(open(f))
        except:
            return {}
    return {}

def save_session_state(user, state):
    with open(session_state_file(user), "w") as f:
        json.dump(state, f, indent=2)

# ----------------------------
# Create / Login
# ---------------------------------------------------------------------------
# Functions responsible for account creation and authentication.
# When a user signs up, their password is securely hashed and stored.
# During login, the entered password is verified against the stored
# hash to authenticate the user.//////////////////////////////////////////////////////////////////////////////////////////////////////////


def create_user(username, password):
    if not username or not password:
        return False, "Username/password required"
    users = load_users()
    u = username.lower().strip()
    if u in users:
        return False, "User exists"

    if u == "admin":
        try:
            key = ctk.CTkInputDialog(text="Enter Admin Setup Key").get_input()
        except:
            return False, "Admin key required"
        if key != ADMIN_SETUP_KEY:
            return False, "Invalid admin key"

    users[u] = hash_password(password)
    save_users(users)
    return True, "Account created"

def authenticate_user(username, password):
    users = load_users()
    u = username.lower().strip()
    if u not in users:
        return False, "User not found"
    if verify_password(users[u], password):
        return True, "Authenticated"
    return False, "Wrong password"


#FULLSCREEN OPENCV SPLASH FUNCTION 
def show_splash_opencv(root_window, video_path):
    """
    TRUE FULLSCREEN splash using native Tkinter to avoid CustomTkinter fullscreen limitations.
    Stretches video to full display resolution.
    """
    import tkinter as tk

    print("=== SPLASH DEBUG ===")
    print("Video exists:", os.path.exists(video_path))

    if not os.path.exists(video_path):
        root_window.after(200, root_window.show_login)
        return

    try:
        root_window.withdraw()
    except:
        pass

    splash = tk.Toplevel()
    splash.attributes("-fullscreen", True)
    splash.configure(bg="black")
    splash.focus_force()

    canvas = tk.Canvas(splash, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Cannot open video")
        splash.destroy()
        root_window.deiconify()
        root_window.after(200, root_window.show_login)
        return

    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()

    def play():
        ret, frame = cap.read()
        if not ret:
            cap.release()
            splash.destroy()
            root_window.deiconify()
            root_window.after(100, root_window.show_login)
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (screen_w, screen_h))

        img = Image.fromarray(frame)
        tkimg = ImageTk.PhotoImage(img)

        canvas.create_image(0, 0, anchor="nw", image=tkimg)
        canvas.img = tkimg

        splash.after(33, play)

    play()
# ----------------------------
# Wikipedia + Intent Model
# ---------------------------------------------------------------------------
# Knowledge retrieval and intent classification system.
# The chatbot attempts to answer questions using:
# 1. Wikipedia summaries for general knowledge queries.
# 2. A trained machine learning intent classifier.
# 3. Predefined responses stored in a FAQ dataset.
# ---------------------------------------------------------------------------
# ----------------------------
wiki = wikipediaapi.Wikipedia(
    language="en",
    user_agent="BaderiaAI/1.0 (contact: ayush@example.com)"
)

GK_WORDS = ["who is","what is","when","where","why","how","formula","minister","president","pm"]

def is_general_question(text: str):
    t = (text or "").lower()
    return any(w in t for w in GK_WORDS)

def wikipedia_answer(query: str):
    try:
        page = wiki.page(query)
        if page.exists():
            return page.summary[:600]
    except Exception as e:
        print("Wikipedia error:", e)
    return None

# Load Intent Model
clf = None
vectorizer = None
INTENT_RESPONSES = {}

try:
    ip = os.path.join(MODEL_DIR, "intent_model.pkl")
    vp = os.path.join(MODEL_DIR, "vectorizer.pkl")

    if os.path.exists(ip) and os.path.exists(vp):
        with open(ip, "rb") as f:
            clf = pickle.load(f)
        with open(vp, "rb") as f:
            vectorizer = pickle.load(f)

    faq = os.path.join(DATA_DIR, "college_faq.json")
    if os.path.exists(faq):
        data = json.load(open(faq, "r"))
        INTENT_RESPONSES = {i["tag"]: i["responses"] for i in data.get("intents", [])}

except Exception as e:
    print("Intent load error:", e)

def predict_intent(text):
    if clf is None or vectorizer is None:
        return None, 0.0
    try:
        X = vectorizer.transform([text])
        tag = clf.predict(X)[0]
        prob = max(clf.predict_proba(X)[0])
        return tag, prob
    except:
        return None, 0.0

def ask_gemini(prompt):
    if not USE_GEMINI:
        return None
    try:
        r = GEMINI_MODEL.generate_content(prompt)
        return getattr(r, "text", None)
    except Exception as e:
        print("Gemini error:", e)
        return None

# ----------------------------
# Image Generation (Pollinations)
# ---------------------------------------------------------------------------
# AI image generation module.
# User prompts requesting images are sent to the Pollinations AI
# image generation API. The generated image is downloaded and stored
# locally so it can be displayed inside the chat interface.
# ---------------------------------------------------------------------------
# ----------------------------
TYPO_LIST = ["genarate","genrate","generat","genarte","ginerate","genart"]

def is_image_request(text):
    t = (text or "").lower()
    keywords = [
        "generate image","create image","make image","image of","photo of","picture of",
        "draw","render"
    ]
    if any(k in t for k in keywords):
        return True
    if "image" in t and any(tp in t for tp in TYPO_LIST):
        return True
    return False

def sanitize_prompt(prompt: str):
    p = prompt.strip()
    low = p.lower()

    blocked = ["modi","kohli","virat","elon","srk"]
    if any(x in low for x in blocked):
        return "a fictional human character, 4k high detail digital portrait"

    if "cute cat" in low:
        return "cute adorable fluffy cat, hd soft lighting, ultra detail"

    if len(p.split()) <= 3:
        return p + ", ultra detail, 4k"

    return p

def generate_image_pollinations(prompt: str):
    safe = sanitize_prompt(prompt)

    try:
        # Encode prompt safely
        safe_prompt = requests.utils.requote_uri(safe)

        # Pollinations working endpoint
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux"

        # Headers to prevent 401 unauthorized error
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*"
        }

        r = requests.get(url, headers=headers, timeout=120)

        if r.status_code != 200:
            print("Pollinations returned:", r.status_code)
            print("URL:", url)
            return None

        fname = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(GENERATED_DIR, fname)

        with open(path, "wb") as f:
            f.write(r.content)

        return fname

    except Exception as e:
        print("Image error:", e)
        return None

# ----------------------------
# Math Memory
# ---------------------------------------------------------------------------
# Mathematical reasoning and memory system.
# This component detects mathematical operations inside user text,
# performs calculations, and remembers the last numerical result.
# This allows follow‑up commands like "double it" or
# "multiply the previous number by 5".
# ---------------------------------------------------------------------------
# ----------------------------
num_re = re.compile(r"(-?\d+(\.\d+)?)")

def find_prev_num(user):
    hist = load_history(user)
    for m in reversed(hist):
        if m.get("role") == "user":
            s = num_re.search(m.get("text",""))
            if s:
                return float(s.group(1))
    return None

def try_math(text, user):
    t = text.lower()

    ops = {
        "multiply":lambda a,b:a*b,
        "multiple":lambda a,b:a*b,
        "times":lambda a,b:a*b,
        "x":lambda a,b:a*b,
        "add":lambda a,b:a+b,
        "plus":lambda a,b:a+b,
        "subtract":lambda a,b:a-b,
        "minus":lambda a,b:a-b,
        "divide":lambda a,b:a/b if b!=0 else None,
        "over":lambda a,b:a/b if b!=0 else None,
    }

    # Explicit: "multiply 5 and 2"
    m = re.search(r"(multiply|multiple|times|x|add|plus|subtract|minus|divide|over)\s+(-?\d+(\.\d+)?)\s+(and|with|by)?\s*(-?\d+(\.\d+)?)+", t)
    if m:
        op = m.group(1)
        a = float(m.group(2))
        b = float(m.group(5))
        fn = ops.get(op)
        if fn:
            return fn(a,b)

    # Store: "store 5" / "set 9"
    s = re.search(r"(i give|store|set|keep)\s+(-?\d+(\.\d+)?)", t)
    if s:
        v = float(s.group(2))
        st = load_session_state(user)
        st["last"] = v
        save_session_state(user, st)
        return f"Stored {v}"

    # "multiply previous number with 5"
    st = load_session_state(user)
    last = st.get("last")
    if last is None:
        last = find_prev_num(user)

    if last is not None:
        # detect new number
        nm = num_re.search(t)
        new = float(nm.group(1)) if nm else None

        for op, fn in ops.items():
            if op in t:
                if new is not None:
                    res = fn(last, new)
                    st["last"] = res
                    save_session_state(user, st)
                    return res

        if "double" in t:
            res = last * 2
            st["last"] = res
            save_session_state(user, st)
            return res

        if "half" in t:
            res = last / 2
            st["last"] = res
            save_session_state(user, st)
            return res

    return None

# ----------------------------
# Reply Engine
# ---------------------------------------------------------------------------
# Core response generation logic of the assistant.
# The engine determines how to respond to user messages by checking:
# • Math expressions
# • Image generation requests
# • Wikipedia knowledge queries
# • Intent classification results
# • Gemini AI fallback responses
# ---------------------------------------------------------------------------
# ----------------------------
def reply_user(text, user):
    text = text.strip()
    t = text.lower()

    if "my name" in t:
        return {"tag":"profile","responses":[f"Your name is {user}."]}

    # Math
    m = try_math(text, user)
    if m is not None:
        if isinstance(m, str):
            return {"tag":"math","responses":[m]}
        return {"tag":"math","responses":[f"The answer is {m}."]}

    # Image
    if is_image_request(t):
        prompt = text
        fname = generate_image_pollinations(prompt)
        if fname:
            return {"tag":"image","image":fname,"responses":["Image generated."]}
        return {"tag":"error","responses":["Image generation failed."]}

    # General question
    if is_general_question(text):
        w = wikipedia_answer(text)
        if w:
            return {"tag":"wiki","responses":[w]}
        g = ask_gemini(f"Answer in few lines: {text}")
        if g:
            return {"tag":"gemini","responses":[g]}

    # Intent model
    tag, prob = predict_intent(text)
    if tag and prob >= 0.55:
        return {"tag":tag,"responses":INTENT_RESPONSES.get(tag,["I don't know about that yet."])}

    # Fallback
    w = wikipedia_answer(text)
    if w:
        return {"tag":"wiki","responses":[w]}

    g = ask_gemini(f"Explain shortly: {text}")
    if g:
        return {"tag":"gemini","responses":[g]}

    return {"tag":"unknown","responses":["I don't know this yet."]}
# ----------------------------
# Flask API Backend
# ---------------------------------------------------------------------------
# Embedded backend server used by the GUI.
# The GUI sends user messages to this Flask API endpoint (/predict).
# The server processes the text using the reply engine and returns
# structured JSON responses to the interface.
# ---------------------------------------------------------------------------
# ----------------------------
flask_app = Flask(__name__)

@flask_app.post("/predict")
def api_predict():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        user = data.get("user", "")
        result = reply_user(text, user)
        return jsonify(result)
    except Exception as e:
        print("Flask predict error:", e)
        return jsonify({"tag":"error","responses":["Server error"]}), 500

def start_flask():
    flask_app.run(host="127.0.0.1", port=5005, debug=False, use_reloader=False)


# GUI APPLICATION — ModernChatApp

class ModernChatApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Global AI Assistant")
        self.geometry("1150x720")
        self.resizable(False, False)

        # STATE
        self.current_user = None
        self.history = []

        self.main_area = None
        self.sidebar_buttons = []
        self.sidebar_anim_running = False

        # Voice + Loading
        self.loading_widget = None
        self.loading_handle = None
        self.loading_dots = 0

        # Start backend
        threading.Thread(target=start_flask, daemon=True).start()

        # Start splash
        self.after(200, lambda: show_splash_opencv(self, SPLASH_VIDEO))

   
    # LOGIN SCREE n
    
    
    def show_login(self):
        # Clear entire window
        for w in self.winfo_children():
            try: w.destroy()
            except: pass

        frame = ctk.CTkFrame(self, width=500, height=360, corner_radius=12)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="🔐 Login to Global AI", font=("Segoe UI", 20, "bold")).place(relx=0.5, rely=0.16, anchor="center")

        self.user_entry = ctk.CTkEntry(frame, width=380, placeholder_text="Username")
        self.user_entry.place(relx=0.5, rely=0.40, anchor="center")

        self.pass_entry = ctk.CTkEntry(frame, width=380, placeholder_text="Password", show="*")
        self.pass_entry.place(relx=0.5, rely=0.55, anchor="center")

        ctk.CTkButton(frame, text="Login", width=150, command=self._login_action).place(relx=0.3, rely=0.80, anchor="center")
        ctk.CTkButton(frame, text="Create Account", width=150, command=self._create_action).place(relx=0.7, rely=0.80, anchor="center")

    def _login_action(self):
        u = (self.user_entry.get() or "").strip().lower()
        p = (self.pass_entry.get() or "").strip()
        ok, msg = authenticate_user(u, p)
        if ok:
            self.current_user = u
            self.history = load_history(u)
            self.show_main()
        else:
            messagebox.showerror("Login Failed", msg)

    def _create_action(self):
        u = (self.user_entry.get() or "").lower().strip()
        p = (self.pass_entry.get() or "").strip()
        ok, msg = create_user(u, p)
        if ok:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

    
    # MAIN LAYOUT (Sidebar + Header + Main Area)//////////////////////////////////////////////////////
    
    def show_main(self):
        for w in self.winfo_children():
            try: w.destroy()
            except: pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # SIDEBAR
        sidebar = ctk.CTkFrame(self, width=220)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=10, pady=10)

        ctk.CTkLabel(sidebar, text="🧠 Baderia AI", font=("Segoe UI", 18, "bold")).pack(pady=12)

        btn_chat = ctk.CTkButton(sidebar, text="💬  Chat", width=180, command=self.show_chat)
        btn_chat.pack(pady=6)

        btn_hist = ctk.CTkButton(sidebar, text="📜  History", width=180, command=self.show_history_page)
        btn_hist.pack(pady=6)

        btn_set = ctk.CTkButton(sidebar, text="⚙️  Settings", width=180, command=self.show_settings)
        btn_set.pack(pady=6)

        self.sidebar_buttons = [
            ("chat", btn_chat),
            ("history", btn_hist),
            ("settings", btn_set)
        ]

        if self.current_user == "admin":
            btn_admin = ctk.CTkButton(sidebar, text="🔒  Admin Panel", width=180, fg_color="#e67e22", command=self.show_admin)
            btn_admin.pack(pady=6)
            self.sidebar_buttons.append(("admin", btn_admin))

        btn_logout = ctk.CTkButton(sidebar, text="🚪  Logout", width=180, fg_color="#e74c3c", command=self.logout)
        btn_logout.pack(side="bottom", pady=12)

        # Animate sidebar
        if not self.sidebar_anim_running:
            self.sidebar_anim_running = True
            self._sidebar_animate()

        # HEADER
        header = ctk.CTkFrame(self, height=60)
        header.grid(row=0, column=1, sticky="ew", padx=10, pady=(10,0))
        ctk.CTkLabel(header, text=f"Signed in as: {self.current_user}", font=("Segoe UI", 14)).pack(padx=10, pady=10)

        # MAIN AREA
        self.main_area = ctk.CTkFrame(self)
        self.main_area.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        # Default tab = Chat
        self.show_chat()

    def _sidebar_animate(self):
        frames = {
            "chat":["💬","🗨️","💭"],
            "history":["📜","📄","📚"],
            "settings":["⚙️","🔧","🛠️"],
            "admin":["🔒","🛡️","🏁"]
        }

        try:
            for key, btn in self.sidebar_buttons:
                seq = frames.get(key, ["•"])
                idx = getattr(btn, "_idx", 0)
                new_text = f"{seq[idx]}  {btn.cget('text').split('  ')[-1]}"
                btn.configure(text=new_text)
                btn._idx = (idx + 1) % len(seq)
        except Exception:
            pass

        if self.sidebar_anim_running:
            self.after(500, self._sidebar_animate)

    # ---------------------------------------------------------
    # CHAT UI
# ---------------------------------------------------------------------------
# Graphical chat interface where conversations occur.
# This section renders user messages, assistant responses,
# generated images, and the input controls for sending
# new messages or voice commands.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def show_chat(self):
        if not self.main_area:
            return

        for w in self.main_area.winfo_children():
            try: w.destroy()
            except: pass

        self.chat_box = ctk.CTkScrollableFrame(self.main_area)
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)

        # Load previous messages
        for m in self.history:
            role = m.get("role")
            if role == "user":
                self._render_user(m.get("text",""))
            elif role == "assistant":
                self._render_bot(m.get("text",""))
            elif role == "image":
                self._render_image(m.get("image"))

        bottom = ctk.CTkFrame(self.main_area)
        bottom.pack(fill="x", padx=10, pady=(0,10))

        self.entry = ctk.CTkEntry(bottom, placeholder_text="Type a message...", width=700)
        self.entry.pack(side="left", fill="x", expand=True, padx=6, pady=8)
        self.entry.bind("<Return>", lambda e:self.send())

        ctk.CTkButton(bottom, text="Send", width=100, command=self.send).pack(side="left", padx=6)
        ctk.CTkButton(bottom, text="🎤", width=60, command=self.voice).pack(side="left", padx=6)

    # Render User Message
    def _render_user(self, text):
        lbl = ctk.CTkLabel(self.chat_box, text=text, fg_color="#0984e3", text_color="white", corner_radius=10, wraplength=650)
        lbl.pack(anchor="e", padx=10, pady=6)

    # Render Bot Message
    def _render_bot(self, text):
        lbl = ctk.CTkLabel(self.chat_box, text=text, fg_color="#16a085", text_color="white", corner_radius=10, wraplength=650)
        lbl.pack(anchor="w", padx=10, pady=6)

    # Render Image
    def _render_image(self, fname):
        if not fname:
            return
        path = os.path.join(GENERATED_DIR, fname)
        if not os.listdir(GENERATED_DIR):
            return

        if not os.path.exists(path):
            self._render_bot("[Image not found]")
            return

        frame = ctk.CTkFrame(self.chat_box)
        frame.pack(anchor="w", padx=10, pady=10)

        img = Image.open(path)
        img.thumbnail((350,350))
        imgtk = ImageTk.PhotoImage(img)

        lbl = ctk.CTkLabel(frame, image=imgtk, text="")
        lbl.image = imgtk
        lbl.pack(side="left", padx=6)

        btns = ctk.CTkFrame(frame)
        btns.pack(side="right", padx=6)

        ctk.CTkButton(btns, text="View", width=80, command=lambda: self.open_full(path)).pack(pady=4)
        ctk.CTkButton(btns, text="Save", width=80, command=lambda: self.save_image(path)).pack(pady=4)
    def open_full(self, path):
        win = ctk.CTkToplevel(self)
        win.title("Image Viewer")
        win.geometry("600x600")

        img = Image.open(path)
        img.thumbnail((580,580))
        imgtk = ImageTk.PhotoImage(img)

        lbl = ctk.CTkLabel(win, image=imgtk, text="")
        lbl.image = imgtk
        lbl.pack(pady=10)

    def save_image(self, path):
        f = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG","*.jpg"),("PNG","*.png")]
        )
        if not f:
            return
        try:
            Image.open(path).save(f)
            messagebox.showinfo("Saved","Image saved successfully!")
        except:
            messagebox.showerror("Error","Failed to save image")

    # ---------------------------------------------------------
    # SEND MESSAGE
# ---------------------------------------------------------------------------
# Handles sending messages from the GUI to the backend API.
# The function captures the user text, stores it in chat history,
# sends the request to the Flask server, and displays the returned
# response inside the chat window.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def send(self):
        text = self.entry.get().strip()
        if not text:
            return

        # Show in chat
        self._render_user(text)
        self.history.append({"role":"user","text":text})
        save_history(self.current_user, self.history)

        self.entry.delete(0, "end")

        # Processing animation
        self._start_loading()

        threading.Thread(target=self._send_api, args=(text,), daemon=True).start()

    def _send_api(self, text):
        try:
            r = requests.post(
                "http://127.0.0.1:5005/predict",
                json={"text":text,"user":self.current_user},
                timeout=60
            )
            data = r.json()
        except Exception as e:
            data = {"tag":"error","responses":["Server offline"]}

        # Update UI in main thread
        self.after(50, lambda:self._handle_response(data))

    def _handle_response(self, data):
        self._stop_loading()

        tag = data.get("tag","")
        responses = data.get("responses",[])
        img = data.get("image")

        if img:
            self.history.append({"role":"image","image":img})
            save_history(self.current_user, self.history)
            self._render_image(img)
            return

        for msg in responses:
            self.history.append({"role":"assistant","text":msg})
            save_history(self.current_user, self.history)
            self._render_bot(msg)

            if tts_engine:
                try:
                    tts_engine.say(msg)
                    tts_engine.runAndWait()
                except:
                    pass

    # ---------------------------------------------------------
    # VOICE INPUT
# ---------------------------------------------------------------------------
# Enables speech‑to‑text interaction with the assistant.
# Audio is captured from the microphone, converted to text
# using Google's speech recognition service, and then processed
# as a normal chat message.
# ---------------------------------------------------------------------------//////////////////////////////////////////////////////
    
    def voice(self):
        if not SR_OK:
            messagebox.showerror("Voice Error","SpeechRecognition not installed.")
            return

        self._render_user("[🎙 Listening...]")

        def worker():
            r = sr.Recognizer()
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src)
                audio = r.listen(src)

            try:
                txt = r.recognize_google(audio, language="en-IN")
            except:
                txt = "I could not understand your voice."

            self.after(50, lambda:self._voice_finish(txt))

        threading.Thread(target=worker, daemon=True).start()

    def _voice_finish(self, text):
        self._render_user(text)
        self.history.append({"role":"user","text":text})
        save_history(self.current_user, self.history)
        self.send_text = text
        self.send()

    # ---------------------------------------------------------
    # LOADING ANIMATION
# ---------------------------------------------------------------------------
# Displays a "Thinking..." animation while the assistant
# processes a request. This improves user experience by
# indicating that the system is actively generating a response.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def _start_loading(self):
        if self.loading_widget:
            return
        self.loading_widget = ctk.CTkLabel(self.chat_box, text="🤖 Thinking")
        self.loading_widget.pack(anchor="w", padx=10, pady=4)

        self.loading_dots = 0
        self._animate_loading()

    def _animate_loading(self):
        if not self.loading_widget:
            return
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.loading_widget.configure(text=f"🤖 Thinking{dots}")
        self.loading_handle = self.after(400, self._animate_loading)

    def _stop_loading(self):
        if self.loading_widget:
            try:
                self.loading_widget.destroy()
            except:
                pass
        self.loading_widget = None
        if self.loading_handle:
            try:
                self.after_cancel(self.loading_handle)
            except:
                pass
        self.loading_handle = None

    # ---------------------------------------------------------
    # HISTORY PAGE
# ---------------------------------------------------------------------------
# Displays previously saved chat conversations for the
# currently logged‑in user. This allows users to review
# earlier interactions with the assistant.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def show_history_page(self):
        for w in self.main_area.winfo_children():
            try: w.destroy()
            except: pass

        box = ctk.CTkScrollableFrame(self.main_area)
        box.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(box, text="Chat History", font=("Segoe UI",20,"bold")).pack(pady=8)

        hist = load_history(self.current_user)

        for h in hist:
            role = h.get("role")
            txt = h.get("text","")
            if role == "user":
                ctk.CTkLabel(box, text=f"👤 {txt}", fg_color="#34495e", corner_radius=10).pack(fill="x", padx=8, pady=4)
            elif role == "assistant":
                ctk.CTkLabel(box, text=f"🤖 {txt}", fg_color="#2ecc71", corner_radius=10).pack(fill="x", padx=8, pady=4)
            elif role == "image":
                ctk.CTkLabel(box, text=f"[Image: {h.get('image')}]", fg_color="#8e44ad", corner_radius=10).pack(fill="x", padx=8, pady=4)

    # ---------------------------------------------------------
    # SETTINGS PAGE
# ---------------------------------------------------------------------------
# Application settings interface.
# Currently allows toggling between light mode and dark mode
# for the graphical user interface.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def show_settings(self):
        for w in self.main_area.winfo_children():
            try: w.destroy()
            except: pass

        frame = ctk.CTkFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Settings", font=("Segoe UI",20,"bold")).pack(pady=10)

        mode_btn = ctk.CTkButton(frame, text="Toggle Light/Dark Mode",
                                 command=self.toggle_theme, width=200)
        mode_btn.pack(pady=10)

    def toggle_theme(self):
        curr = ctk.get_appearance_mode().lower()
        if curr == "dark":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    # ---------------------------------------------------------
    # ADMIN PANEL
# ---------------------------------------------------------------------------
# Administrative dashboard accessible only to the admin account.
# Provides basic analytics such as the number of registered users
# and the total number of messages stored in chat histories.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def show_admin(self):
        if self.current_user != "admin":
            messagebox.showerror("Access Denied","Only admin can access this page")
            return

        for w in self.main_area.winfo_children():
            try: w.destroy()
            except: pass

        frame = ctk.CTkFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Admin Panel", font=("Segoe UI",20,"bold")).pack(pady=10)

        users = load_users()
        ctk.CTkLabel(frame, text=f"Total Users: {len(users)}").pack(pady=4)

        hist_count = sum(len(load_history(u)) for u in users)
        ctk.CTkLabel(frame, text=f"Total Messages: {hist_count}").pack(pady=4)

    # ---------------------------------------------------------
    # LOGOUT
# ---------------------------------------------------------------------------
# Ends the current user session and clears loaded history data.
# The application returns to the login screen so another user
# can sign in.
# ---------------------------------------------------------------------------
    # ---------------------------------------------------------
    def logout(self):
        self.sidebar_anim_running = False
        self.current_user = None
        self.history = []
        self.show_login()
# ----------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------
# Entry point of the application.
# Creates an instance of the main GUI class and starts
# the Tkinter event loop that keeps the interface running.
# ---------------------------------------------------------------------------
# ----------------------------
if __name__ == "__main__":
    app = ModernChatApp()
    app.mainloop()
