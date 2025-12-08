# analysis/taste_mirror_3_1.py - code created with assistance from AI
import os, ast, logging
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RAW_PATH = os.path.join("data", "raw", "RAW_recipes.csv")
PROCESSED_PATH = os.path.join("data", "processed", "recipes_clean.csv")
OUTDIR = os.path.join("analysis", "outputs")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)

def parse_list(s):
    try:
        return ast.literal_eval(s)
    except Exception:
        return []

def parse_nutrition(s):
    """RAW_recipes nutrition order:
    [calories, total_fat_PDV, sugar_PDV, sodium_PDV,
     protein_PDV, saturated_fat_PDV, carbohydrates_PDV]
    """
    try:
        vals = ast.literal_eval(s)
        if isinstance(vals, (list, tuple)) and len(vals) == 7:
            return pd.Series(vals)
    except Exception:
        pass
    return pd.Series([np.nan] * 7)

def winsorize(series: pd.Series, lower=0.01, upper=0.99) -> pd.Series:
    lo, hi = series.quantile(lower), series.quantile(upper)
    return series.clip(lower=lo, upper=hi)

def main():
    os.makedirs(OUTDIR, exist_ok=True)

    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(f"Missing {RAW_PATH}. Place RAW_recipes.csv in data/raw/")

    logging.info(f"Loading {RAW_PATH}")
    df = pd.read_csv(RAW_PATH)

    # Parse ingredients
    if "ingredients" in df.columns:
        df["ingredients"] = df["ingredients"].apply(parse_list)
    else:
        df["ingredients"] = [[] for _ in range(len(df))]

    # Parse nutrition
    nutr_cols = [
        "calories", "total_fat_PDV", "sugar_PDV", "sodium_PDV",
        "protein_PDV", "saturated_fat_PDV", "carbohydrates_PDV"
    ]
    if "nutrition" in df.columns:
        df[nutr_cols] = df["nutrition"].apply(parse_nutrition)
    else:
        for c in nutr_cols:
            df[c] = np.nan

    # Keep analysis columns
    keep_cols = ["id", "name", "minutes", "n_steps", "n_ingredients", "ingredients"] + nutr_cols
    df_clean = df[[c for c in keep_cols if c in df.columns]].copy()

    # Ensure numeric
    for c in nutr_cols:
        df_clean[c] = pd.to_numeric(df_clean[c], errors="coerce")

    # Save processed
    df_clean.to_csv(PROCESSED_PATH, index=False)
    logging.info(f"Saved processed dataset → {PROCESSED_PATH} (rows={len(df_clean)})")

    # Summary stats
    num = df_clean[nutr_cols].replace([np.inf, -np.inf], np.nan)
    summary = num.describe().T
    median = num.median(numeric_only=True)

    summary.to_csv(os.path.join(OUTDIR, "summary_stats.csv"))
    median.to_csv(os.path.join(OUTDIR, "median_stats.csv"), header=["median"])
    logging.info("Saved summary_stats.csv and median_stats.csv")

    # ------------ Correlation heatmap (Spearman; robust to outliers) ------------
    plt.figure(figsize=(9, 7))
    corr = num.corr(method="spearman")
    sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, center=0, square=True, fmt=".2f")
    plt.title("Nutrient Correlations (Spearman)")
    plt.tight_layout()
    heatmap_path = os.path.join(OUTDIR, "corr_heatmap_spearman.png")
    plt.savefig(heatmap_path, dpi=200)
    plt.close()
    logging.info(f"Saved → {heatmap_path}")

    # ------------ Calories distributions (winsorized + log-scale) ------------
    if "calories" in num.columns:
        calories = num["calories"].dropna()
        if len(calories) > 0:
            # Winsorized (1–99%) to avoid a single huge bar
            cal_w = winsorize(calories, 0.01, 0.99)
            mean_v, med_v = cal_w.mean(), cal_w.median()

            plt.figure(figsize=(10, 6))
            ax = sns.histplot(cal_w, bins="auto", kde=True)
            ax.axvline(mean_v, linestyle="--", linewidth=1.5, label=f"Mean: {mean_v:.0f}")
            ax.axvline(med_v, linestyle="-.", linewidth=1.5, label=f"Median: {med_v:.0f}")
            plt.legend()
            plt.xlabel("Calories (winsorized 1–99%)")
            plt.title("Calories Distribution (Trimmed Outliers)")
            plt.tight_layout()
            hist_trim_path = os.path.join(OUTDIR, "calories_hist_trimmed.png")
            plt.savefig(hist_trim_path, dpi=200)
            plt.close()
            logging.info(f"Saved → {hist_trim_path}")

            # Log-scale version for full range visibility
            plt.figure(figsize=(10, 6))
            ax = sns.histplot(calories[calories > 0], bins="auto")
            ax.set_xscale("log")
            plt.xlabel("Calories (log scale)")
            plt.title("Calories Distribution (Log Scale)")
            plt.tight_layout()
            hist_log_path = os.path.join(OUTDIR, "calories_hist_log.png")
            plt.savefig(hist_log_path, dpi=200)
            plt.close()
            logging.info(f"Saved → {hist_log_path}")

    # ------------ Optional: Top ingredients ------------
    flat_ings = [ing for sub in df_clean["ingredients"] for ing in (sub if isinstance(sub, list) else [])]
    if flat_ings:
        top = Counter(flat_ings).most_common(15)
        labels, counts = zip(*top)
        plt.figure(figsize=(10, 7))
        plt.barh(labels[::-1], counts[::-1])
        plt.title("Top 15 Ingredients")
        plt.tight_layout()
        ing_path = os.path.join(OUTDIR, "top_ingredients.png")
        plt.savefig(ing_path, dpi=200)
        plt.close()
        logging.info(f"Saved → {ing_path}")

    logging.info("completed.")

if __name__ == "__main__":
    main()
