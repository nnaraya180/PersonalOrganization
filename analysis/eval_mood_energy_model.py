"""
Evaluate the accuracy of the trained mood and energy models.
Prints classification accuracy and confusion matrix for both models.
"""
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

DATA_PATH = "../Data/processed/nutrition_labels_clean.csv"
MOOD_MODEL_PATH = "../backend/ml/mood_model.pkl"
ENERGY_MODEL_PATH = "../backend/ml/energy_model.pkl"
MOOD_LE_PATH = "../backend/ml/mood_label_encoder.pkl"
ENERGY_LE_PATH = "../backend/ml/energy_label_encoder.pkl"

# Load data
df = pd.read_csv(DATA_PATH)
FEATURES = [
    "Calories",
    "Total Fat (g)",
    "Total Sugars (g)",
    "Carbohydrates (Carbs) (g)",
    "Protein (g)",
]
df = df.dropna(subset=FEATURES + ["Mood", "Energy"])

# Load encoders
mood_le = joblib.load(MOOD_LE_PATH)
energy_le = joblib.load(ENERGY_LE_PATH)
df["Mood_label"] = mood_le.transform(df["Mood"].astype(str))
df["Energy_label"] = energy_le.transform(df["Energy"].astype(str))

X = df[FEATURES]
y_mood = df["Mood_label"]
y_energy = df["Energy_label"]

# Load models
mood_model = joblib.load(MOOD_MODEL_PATH)
energy_model = joblib.load(ENERGY_MODEL_PATH)

# Predict
mood_pred = np.round(mood_model.predict(X)).astype(int)
energy_pred = np.round(energy_model.predict(X)).astype(int)

# Clamp predictions to valid label range
mood_pred = np.clip(mood_pred, 0, len(mood_le.classes_)-1)
energy_pred = np.clip(energy_pred, 0, len(energy_le.classes_)-1)

print("Mood Model Accuracy:")
print("Accuracy:", accuracy_score(y_mood, mood_pred))
print("Classification Report:\n", classification_report(y_mood, mood_pred, target_names=mood_le.classes_))
print("Confusion Matrix:\n", confusion_matrix(y_mood, mood_pred))
print()
print("Energy Model Accuracy:")
print("Accuracy:", accuracy_score(y_energy, energy_pred))
print("Classification Report:\n", classification_report(y_energy, energy_pred, target_names=energy_le.classes_))
print("Confusion Matrix:\n", confusion_matrix(y_energy, energy_pred))
