# analysis/I_10_problem_2_1.py
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RAW_PATH = "/Users/neilnarayanan/code/personal-assistant/Data/Raw/nutrition_labels.csv"
PROCESSED_PATH = "/Users/neilnarayanan/code/personal-assistant/Data/processed/nutrition_labels_clean.csv"
OUTPUT_DIR = "/Users/neilnarayanan/code/personal-assistant/analysis/outputs/2_1"

TARGET_COLS = ["Total Fat", "Total Sugars", "Carbohydrates (Carbs)", "Protein"]

def to_grams(value):
    """Parse strings like '48.2 g', '48g', '120 mg', '1 kg', '-', '' into float grams."""
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s in {"", "-", "—", "na", "n/a", "none"}:
        return None
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    num = float(m.group(1))
    if "mg" in s:
        return num / 1000.0
    if "kg" in s:
        return num * 1000.0
    if "g" in s:
        return num
    return num  # assume grams if unspecified

def clean_and_save():
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    df = pd.read_csv(RAW_PATH)

    missing = [c for c in TARGET_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing expected column(s) in CSV: {missing}")

    rename_map = {}
    for col in TARGET_COLS:
        df[col] = df[col].apply(to_grams)
        rename_map[col] = f"{col} (g)"
    df = df.rename(columns=rename_map)

    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Saved cleaned dataset to: {PROCESSED_PATH}\n")
    print("Dtypes (nutrients should be float):")
    print(df[[rename_map[c] for c in TARGET_COLS]].dtypes, "\n")
    print("Preview:")
    print(df.head(10).to_string(index=False))

    return df

def ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def plot_nutrient_distributions(df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nutrient_cols = [f"{c} (g)" for c in TARGET_COLS if f"{c} (g)" in df.columns]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.flatten()

    for ax, col in zip(axes, nutrient_cols):
        ax.hist(df[col].dropna(), bins=30, alpha=0.9)
        ax.set_title(col)
        ax.set_xlabel("grams")
        ax.set_ylabel("count")

    for k in range(len(nutrient_cols), len(axes)):
        axes[k].set_visible(False)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "nutrient_distributions.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"Saved: {out}")

def plot_calories_vs_energy_box(df):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Ensure numeric Calories
    df["Calories"] = pd.to_numeric(df["Calories"], errors="coerce")

    # Drop rows missing either field
    df_box = df.dropna(subset=["Calories", "Energy"]).copy()

    # Plot Calories by Energy category
    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df_box, x="Energy", y="Calories", palette="pastel")
    plt.title("Calories vs. Energy Levels")
    plt.xlabel("Energy Category")
    plt.ylabel("Calories")
    plt.tight_layout()

    out = os.path.join(OUTPUT_DIR, "calories_vs_energy_boxplot.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"Saved: {out}")

def main():
    sns.set_theme()
    df = clean_and_save()
    plot_nutrient_distributions(df)
    plot_calories_vs_energy_box(df)

if __name__ == "__main__":
    main()
