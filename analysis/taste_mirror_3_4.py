# analysis/taste_mirror_3_4.py
# ------------------------------------------------------------
# Problem 3.4 (Stretch) - Logistic Regression (Mood Spectrum)
# - Trains Logistic Regression on processed recipe data
# - Visualizes:
#     1) Normalized Confusion Matrix
#     2) Actual vs Predicted Mood mapped to [-1, 1] scale
# - Computes Pearson correlation between actual/predicted mood
# ------------------------------------------------------------

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from scipy.stats import pearsonr

# ---------- File paths ----------
PROCESSED = "data/processed/recipes_clean.csv"
INTERACTIONS = "data/raw/RAW_interactions.csv"
OUTDIR = Path("analysis/outputs/3_4")
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def derive_mood_label(r):
    """Simple rating→label mapping: <=2=neg(0), 3=neu(1), >=4=pos(2)."""
    if r >= 4:
        return 2
    elif r <= 2:
        return 0
    else:
        return 1

# ---------- Load & merge ----------
recipes = pd.read_csv(PROCESSED)
inter = pd.read_csv(INTERACTIONS, usecols=["recipe_id", "rating"])
inter["mood_label"] = inter["rating"].apply(derive_mood_label)
df = inter.merge(recipes, left_on="recipe_id", right_on="id", how="inner")

# ---------- Feature selection ----------
feature_cols = [
    "calories", "total_fat_PDV", "sugar_PDV", "sodium_PDV",
    "protein_PDV", "saturated_fat_PDV", "carbohydrates_PDV",
    "minutes", "n_steps", "n_ingredients"
]
X = df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(df.median(numeric_only=True))
y = df["mood_label"].astype(int)

# ---------- Scale numeric features ----------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------- Train/test split ----------
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, stratify=y, random_state=42
)

# ---------- Train Logistic Regression ----------
logreg = LogisticRegression(max_iter=300, class_weight="balanced")
logreg.fit(X_train, y_train)
y_pred = logreg.predict(X_test)

# ---------- Console metrics ----------
print("\n=== Logistic Regression (Supervised) ===")
print(classification_report(y_test, y_pred, digits=3))

# ---------- 1) Normalized Confusion Matrix ----------
cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
cmn = cm.astype(float) / cm.sum(axis=1, keepdims=True)

fig, ax = plt.subplots(figsize=(6.5, 5.5))
im = ax.imshow(cmn, interpolation="nearest", cmap="Blues")
ax.figure.colorbar(im, ax=ax)
ax.set(
    xticks=np.arange(3), yticks=np.arange(3),
    xticklabels=["neg", "neu", "pos"], yticklabels=["neg", "neu", "pos"],
    xlabel="Predicted", ylabel="True",
    title="Logistic Regression (Normalized Confusion Matrix)"
)
# Annotate cells
for i in range(cmn.shape[0]):
    for j in range(cmn.shape[1]):
        ax.text(j, i, f"{cmn[i, j]:.2f}",
                ha="center", va="center",
                color=("white" if cmn[i, j] > cmn.max()/2 else "black"))
fig.tight_layout()
fig.savefig(OUTDIR / "logreg_confusion.png", dpi=200)
plt.close(fig)

# ---------- 2) Actual vs Predicted (mapped to -1 → 1) ----------
# Map mood categories to continuous spectrum
mood_map = {0: -1, 1: 0, 2: 1}
y_test_cont = y_test.map(mood_map)
y_pred_cont = pd.Series(y_pred).map(mood_map)

# Compute Pearson correlation
corr, _ = pearsonr(y_test_cont, y_pred_cont)
print(f"Correlation between actual and predicted mood: {corr:.3f}")

# Add small jitter for visibility
rng = np.random.default_rng(42)
jitter = 0.05
yt_actual = y_test_cont.to_numpy() + rng.normal(0, jitter, size=len(y_test_cont))
yt_pred = y_pred_cont.to_numpy() + rng.normal(0, jitter, size=len(y_pred_cont))

# Scatter plot
fig, ax = plt.subplots(figsize=(7.5, 5.5))
ax.scatter(yt_actual, yt_pred, s=25, alpha=0.6)
ax.set_xlabel("Actual Mood (-1=neg, 0=neu, 1=pos)")
ax.set_ylabel("Predicted Mood (-1=neg, 0=neu, 1=pos)")
ax.set_title(f"Actual vs Predicted Mood (LogReg, Spectrum) — r = {corr:.2f}")

# Diagonal reference line
lims = [-1.1, 1.1]
ax.plot(lims, lims, linestyle="--", linewidth=1, color="gray")
ax.set_xlim(lims)
ax.set_ylim(lims)
ax.set_xticks([-1, 0, 1])
ax.set_yticks([-1, 0, 1])
fig.tight_layout()
fig.savefig(OUTDIR / "logreg_actual_vs_pred_spectrum.png", dpi=200)
plt.close(fig)

print("\nArtifacts saved to:", OUTDIR.resolve())
print("Files: logreg_confusion.png, logreg_actual_vs_pred_spectrum.png")


