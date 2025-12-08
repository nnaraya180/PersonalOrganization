# analysis/taste_mirror_3_2.py - code created with assistance from AI
# ------------------------------------------------------------
# Supervised Learning - Random Forest Classifier
# Goal: Predict user "mood" (negative / neutral / positive)
#       using combined information from review ratings and text.
#
# Key idea:
# 1. Use both star ratings and VADER sentiment of review text
#    to derive a proxy mood label.
# 2. Train a Random Forest on recipe-level features
#    (nutritional + preparation features).
# 3. Evaluate with accuracy, F1, and confusion matrix.
#
# Features used:
#   - calories
#   - total_fat_PDV
#   - sugar_PDV
#   - sodium_PDV
#   - protein_PDV
#   - saturated_fat_PDV
#   - carbohydrates_PDV
#   - minutes (prep time)
#   - n_steps (recipe steps)
#   - n_ingredients
# ------------------------------------------------------------

import os
import json
from pathlib import Path
import argparse
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

# ---------- Sentiment Analysis (VADER) ----------
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# helper: ensure VADER lexicon is available
def _ensure_vader():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)

# ---------- Default File Paths ----------
PROCESSED_RECIPES = os.path.join("data", "processed", "recipes_clean.csv")
RAW_INTERACTIONS = os.path.join("data", "raw", "RAW_interactions.csv")
OUTDIR = os.path.join("analysis", "outputs", "3_2")


# ---------- Command-Line Arguments ----------
def parse_args():
    """
    Allows flexible control when running the script:
      e.g. python taste_mirror_3_2.py --pos_thr 0.55 --neg_thr -0.15
    """
    p = argparse.ArgumentParser(description="Problem 3.2: RF with Rating + VADER sentiment proxy mood")
    p.add_argument("--recipes", type=str, default=PROCESSED_RECIPES,
                   help="Path to processed recipes CSV (from taste_mirror_3_1.py)")
    p.add_argument("--interactions", type=str, default=RAW_INTERACTIONS,
                   help="Path to RAW_interactions.csv")
    p.add_argument("--outdir", type=str, default=OUTDIR, help="Output directory")
    p.add_argument("--min_reviews", type=int, default=1, help="Min interactions per recipe to keep")
    p.add_argument("--test_size", type=float, default=0.2, help="Test fraction")
    p.add_argument("--n_estimators", type=int, default=300, help="Number of trees in RandomForest")
    p.add_argument("--max_depth", type=int, default=None, help="Maximum depth (None = unlimited)")
    p.add_argument("--random_state", type=int, default=42, help="Random seed for reproducibility")
    # Label-blending weights and thresholds
    p.add_argument("--w_rating", type=float, default=0.6, help="Weight for rating in combined score")
    p.add_argument("--w_text", type=float, default=0.4, help="Weight for VADER compound in combined score")
    p.add_argument("--pos_thr", type=float, default=0.45, help="Threshold >= for POS label")
    p.add_argument("--neg_thr", type=float, default=-0.25, help="Threshold <= for NEG label")
    return p.parse_args()


# ---------- Rating Mapping ----------
# This creates a stricter mapping for the 1–5 star ratings.
# The goal is to make 5 stars strongly positive, 4 stars only slightly positive,
# and 3 stars slightly negative — to counteract user positivity bias.
RATING_MAP = {5: 1.00, 4: 0.25, 3: -0.05, 2: -0.60, 1: -1.00}

def rating_to_score(r):
    """Convert numeric rating (1–5) to a scaled sentiment score."""
    try:
        r = int(float(r))
    except Exception:
        return np.nan
    return RATING_MAP.get(r, np.nan)


# ---------- Combine Rating + Text Sentiment ----------
def combined_label(rating, review, w_rating=0.6, w_text=0.4, pos_thr=0.45, neg_thr=-0.25, sia=None):
    """
    Blend numeric rating and VADER text sentiment into one combined mood label.

    Steps:
      1. Convert rating to numeric 'rating_score' (RATING_MAP above)
      2. Use VADER to compute compound sentiment of the review text (-1 to +1)
      3. Combine using weighted average: 0.6 * rating + 0.4 * text
      4. Apply thresholds:
           >= pos_thr  → positive (2)
           <= neg_thr  → negative (0)
           else        → neutral (1)
    """
    rs = rating_to_score(rating)
    if np.isnan(rs):
        return np.nan
    text = "" if pd.isna(review) else str(review)
    c = sia.polarity_scores(text)["compound"]  # VADER compound score
    combo = w_rating * rs + w_text * c
    if combo >= pos_thr:
        return 2
    elif combo <= neg_thr:
        return 0
    else:
        return 1


# ---------- Load Processed Recipes ----------
def load_recipes(processed_path: str) -> pd.DataFrame:
    """
    Loads the processed recipe data created in taste_mirror_3_1.py.
    Keeps only columns required for modeling.
    """
    df = pd.read_csv(processed_path)
    expected = [
        "id", "name", "minutes", "n_steps", "n_ingredients",
        "calories", "total_fat_PDV", "sugar_PDV", "sodium_PDV",
        "protein_PDV", "saturated_fat_PDV", "carbohydrates_PDV"
    ]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Processed recipes missing: {missing}. Re-run analysis/taste_mirror_3_1.py.")
    return df.rename(columns={"id": "recipe_id"})


# ---------- Load Interactions and Create Mood Label ----------
def load_interactions(interactions_path: str, min_reviews: int,
                      w_rating: float, w_text: float, pos_thr: float, neg_thr: float) -> pd.DataFrame:
    """
    Loads Food.com interaction data (ratings + reviews),
    filters to recipes with sufficient reviews,
    and applies combined_label() to generate proxy mood labels.
    """
    _ensure_vader()
    sia = SentimentIntensityAnalyzer()

    inter = pd.read_csv(interactions_path, usecols=["recipe_id", "rating", "review", "date"])
    # Keep only recipes with at least 'min_reviews' user interactions
    vc = inter.recipe_id.value_counts()
    keep = vc[vc >= min_reviews].index
    inter = inter[inter.recipe_id.isin(keep)].copy()

    # Create the mood label for each review
    inter["mood_label"] = inter.apply(
        lambda r: combined_label(
            r["rating"], r["review"], w_rating=w_rating, w_text=w_text,
            pos_thr=pos_thr, neg_thr=neg_thr, sia=sia
        ),
        axis=1
    )
    inter = inter.dropna(subset=["mood_label"]).copy()
    inter["mood_label"] = inter["mood_label"].astype(int)
    return inter


# ---------- Build Feature Matrix ----------
def build_feature_matrix(df_merged: pd.DataFrame):
    """
    Selects numeric features (nutritional + prep) as X,
    and the derived mood_label as y.
    """
    feature_cols = [
        "calories", "total_fat_PDV", "sugar_PDV", "sodium_PDV",
        "protein_PDV", "saturated_fat_PDV", "carbohydrates_PDV",
        "minutes", "n_steps", "n_ingredients",
    ]
    X = df_merged[feature_cols].copy()
    y = df_merged["mood_label"].copy()
    return X, y, feature_cols


# ---------- Confusion Matrix Plotting ----------
def save_confusion_matrices(cm: np.ndarray, outdir: Path):
    """
    Saves two confusion matrices (raw + normalized) with blue–white–red color map.
    Blue = negative predictions, red = positive.
    """
    labels = ["neg", "neu", "pos"]

    # Raw counts
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation="nearest", cmap="bwr")
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=np.arange(cm.shape[1]), yticks=np.arange(cm.shape[0]),
           xticklabels=labels, yticklabels=labels,
           xlabel="Predicted", ylabel="True", title="Confusion Matrix")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm[i, j]:d}",
                    ha="center", va="center",
                    color=("white" if cm[i, j] > cm.max()/2 else "black"))
    fig.tight_layout()
    fig.savefig(outdir / "confusion_matrix.png", dpi=200)
    plt.close(fig)

    # Normalized version
    cmn = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cmn, interpolation="nearest", cmap="bwr")
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=np.arange(cmn.shape[1]), yticks=np.arange(cmn.shape[0]),
           xticklabels=labels, yticklabels=labels,
           xlabel="Predicted", ylabel="True", title="Confusion Matrix (Normalized)")
    for i in range(cmn.shape[0]):
        for j in range(cmn.shape[1]):
            ax.text(j, i, f"{cmn[i, j]:.2f}",
                    ha="center", va="center",
                    color=("white" if cmn[i, j] > cmn.max()/2 else "black"))
    fig.tight_layout()
    fig.savefig(outdir / "confusion_matrix_normalized.png", dpi=200)
    plt.close(fig)


# ---------- Main Pipeline ----------
def main():
    warnings.filterwarnings("ignore")
    args = parse_args()

    # Prepare output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Load datasets
    recipes = load_recipes(args.recipes)
    inter = load_interactions(
        args.interactions, args.min_reviews,
        w_rating=args.w_rating, w_text=args.w_text,
        pos_thr=args.pos_thr, neg_thr=args.neg_thr
    )

    # Merge review interactions (with mood label) and recipe nutritional info
    df = inter.merge(recipes, on="recipe_id", how="inner")

    # 2. Build features (X) and labels (y)
    X, y, feature_cols = build_feature_matrix(df)

    # 3. Split into train/test subsets (stratified by mood label)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state, stratify=y
    )

    # 4. Preprocessing: Impute missing numeric values
    pre = ColumnTransformer([("num", SimpleImputer(strategy="median"), feature_cols)])

    # 5. Define the model: Random Forest
    rf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state,
        n_jobs=-1,
        class_weight="balanced_subsample",  # helps offset class imbalance
    )

    # 6. Combine preprocessing + model into one pipeline
    pipe = Pipeline(steps=[("pre", pre), ("rf", rf)])

    # 7. Train (fit) the model on training data
    pipe.fit(X_train, y_train)

    # 8. Evaluate on test data
    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1m = f1_score(y_test, y_pred, average="macro")
    report = classification_report(y_test, y_pred,
                                   target_names=["negative(0)", "neutral(1)", "positive(2)"],
                                   digits=3)

    # 9. Save confusion matrices
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
    save_confusion_matrices(cm, outdir)

    # 10. Feature importance analysis
    rf_fit = pipe.named_steps["rf"]
    importances = rf_fit.feature_importances_
    fi = pd.DataFrame({"feature": feature_cols, "importance": importances}).sort_values("importance", ascending=False)
    fi.to_csv(outdir / "feature_importances.csv", index=False)

    # quick top-8 bar plot
    topk = fi.head(8)
    plt.figure(figsize=(7, 4))
    plt.barh(topk["feature"][::-1], topk["importance"][::-1])
    plt.title("Top Feature Importances (Random Forest)")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(outdir / "top_features.png", dpi=200)
    plt.close()

    # 11. Save metrics to text file
    class_counts = y.value_counts().to_dict()
    with open(outdir / "metrics.txt", "w") as f:
        f.write("Problem 3.2 - RF with Rating + VADER sentiment\n")
        f.write(f"Rows after merge: {len(df)}\n")
        f.write(f"Class counts: {json.dumps(class_counts)}\n\n")
        f.write(f"Accuracy: {acc:.4f}\n")
        f.write(f"F1 (macro): {f1m:.4f}\n\n")
        f.write("Classification Report:\n")
        f.write(report)

    # 12. Print concise console summary
    print("=== Problem 3.2 Summary ===")
    print(f"Rows: {len(df)} | Class counts: {class_counts}")
    print(f"Accuracy: {acc:.3f} | F1-macro: {f1m:.3f}")
    print("\nTop features:")
    print(fi.head(8).to_string(index=False))
    print(f"\nArtifacts saved to: {outdir.resolve()}")
    print("Files: metrics.txt, confusion_matrix.png, confusion_matrix_normalized.png, feature_importances.csv, top_features.png")


if __name__ == "__main__":
    main()
