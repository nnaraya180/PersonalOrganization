# analysis/I_10_problem_2_3.py
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

PROCESSED_PATH = "/Users/neilnarayanan/code/personal-assistant/Data/processed/nutrition_labels_clean.csv"
OUTPUT_DIR = "/Users/neilnarayanan/code/personal-assistant/analysis/outputs/2_3"
LABELED_CSV = "/Users/neilnarayanan/code/personal-assistant/Data/processed/nutrition_labels_kmeans.csv"
CLUSTER_SUMMARY_CSV = "/Users/neilnarayanan/code/personal-assistant/Data/processed/nutrition_labels_kmeans_summary.csv"

# === Features selected (explicit) ===
FEATURES = [
    "Calories",
    "Total Fat (g)",
    "Total Sugars (g)",
    "Carbohydrates (Carbs) (g)",
    "Protein (g)",
]

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import numpy as np
import os

# --- Determine optimal k via Elbow + Silhouette ---
def evaluate_k_values(X_scaled, output_dir, k_min=2, k_max=10, random_state=42):
    inertias = []
    silhouettes = []
    k_values = range(k_min, k_max + 1)

    print(f"[KMeans Evaluation] Testing k={k_min}–{k_max}")
    for k in k_values:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        sil = silhouette_score(X_scaled, labels)
        silhouettes.append(sil)
        print(f"  k={k}: inertia={km.inertia_:.0f}, silhouette={sil:.4f}")

    # --- Plot Elbow ---
    plt.figure(figsize=(7,5))
    plt.plot(k_values, inertias, marker='o')
    plt.title("Elbow Method")
    plt.xlabel("Number of Clusters")
    plt.ylabel("Inertia")
    plt.tight_layout()
    elbow_path = os.path.join(output_dir, "kmeans_elbow.png")
    plt.savefig(elbow_path, dpi=200)
    plt.close()

    # --- Plot Silhouette ---
    plt.figure(figsize=(7,5))
    plt.plot(k_values, silhouettes, color='orange', marker='o')
    plt.title("Silhouette Scores for Different k")
    plt.xlabel("Number of Clusters")
    plt.ylabel("Silhouette Score")
    plt.tight_layout()
    sil_path = os.path.join(output_dir, "kmeans_silhouette.png")
    plt.savefig(sil_path, dpi=200)
    plt.close()

    # --- Pick best k ---
    best_k = k_values[int(np.argmax(silhouettes))]
    print(f"[KMeans Evaluation] Selected k={best_k} (max silhouette={max(silhouettes):.3f})")

    return best_k, elbow_path, sil_path


def main(k_manual: int | None = None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load and select features
    df = pd.read_csv(PROCESSED_PATH)
    X = df[FEATURES].copy()
    for c in FEATURES:
        X[c] = pd.to_numeric(X[c], errors="coerce")

    # Drop rows with missing values in features
    idx = X.dropna().index
    X = X.loc[idx].reset_index(drop=True)
    df_model = df.loc[idx].reset_index(drop=True)

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --- Choose k (manual override, else evaluate) ---
    if k_manual is not None:
        optimal_k = int(k_manual)
        print(f"[KMeans] Using manual k={optimal_k}")
        elbow_path = sil_path = None
    else:
        optimal_k, elbow_path, sil_path = evaluate_k_values(X_scaled, OUTPUT_DIR)
        print(f"Elbow plot saved at: {elbow_path}")
        print(f"Silhouette plot saved at: {sil_path}")

    # --- Final KMeans ---
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    df_model["Cluster"] = labels

    # --- PCA 2D for visualization ---
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    pc1, pc2 = pca.explained_variance_ratio_[:2] * 100

    plt.figure(figsize=(7, 6))
    sc = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, alpha=0.9, edgecolor="k")
    plt.xlabel(f"PC1 ({pc1:.1f}% var)")
    plt.ylabel(f"PC2 ({pc2:.1f}% var)")
    plt.title(f"K-Means Clusters (k={optimal_k}) in PCA Space")
    cbar = plt.colorbar(sc); cbar.set_label("Cluster")
    plt.tight_layout()
    pca_path = os.path.join(OUTPUT_DIR, "kmeans_pca_scatter.png")
    plt.savefig(pca_path, dpi=200); plt.close()
    print(f"Saved: {pca_path}")

    # --- Cluster means table ---
    summary = df_model.groupby("Cluster")[FEATURES].mean().round(2)
    summary["n"] = df_model["Cluster"].value_counts().sort_index().values
    summary.to_csv(CLUSTER_SUMMARY_CSV)
    print(f"Saved: {CLUSTER_SUMMARY_CSV}")

    # --- Labeled CSV ---
    out_df = df.loc[idx].copy()
    out_df["Cluster"] = labels
    out_df.to_csv(LABELED_CSV, index=False)
    print(f"Saved: {LABELED_CSV}")

    # --- Choose k ---
    # if k_manual is None:
    #     k_list = list(range(2, 11))
    #     sils = []
    #     for k in k_list:
    #         km = KMeans(n_clusters=k, random_state=42, n_init=10)
    #         labels = km.fit_predict(X_scaled)
    #         sils.append(silhouette_score(X_scaled, labels))
    #     best_i = int(np.argmax(sils))
    #     k_opt = k_list[best_i]
    #     print(f"[KMeans] Auto-selected k={k_opt} (silhouette={sils[best_i]:.3f})")
    # else:
    #     k_opt = int(k_manual)
    #     print(f"[KMeans] Using manual k={k_opt}")

   

if __name__ == "__main__":
    # To force a specific k, pass an int: main(k_manual=3)
    main()
