import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.utils import shuffle
import pickle

# Paths
DATA_PATH = "data/college_faq.json"
MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

# Load JSON Data
with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

questions = []
labels = []

# Load patterns and tags
for intent in data["intents"]:
    for pattern in intent["patterns"]:
        questions.append(pattern)
        labels.append(intent["tag"])

# Shuffle for better training
questions, labels = shuffle(questions, labels, random_state=42)

# TF-IDF Vectorizer
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(questions)

# Model
model = LogisticRegression(max_iter=1000)
model.fit(X, labels)

# Save vectorizer
with open(os.path.join(MODEL_DIR, "vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)

# Save model
with open(os.path.join(MODEL_DIR, "intent_model.pkl"), "wb") as f:
    pickle.dump(model, f)

print("🎉 Training Completed Successfully!")


