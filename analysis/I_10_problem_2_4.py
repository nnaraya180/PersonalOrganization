import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# ---- Paths ----
PROCESSED_PATH = "/Users/neilnarayanan/code/personal-assistant/Data/processed/nutrition_labels_clean.csv"
OUTPUT_DIR = "/Users/neilnarayanan/code/personal-assistant/analysis/outputs/2_4"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- Features (match your cleaned columns) ----
FEATURES = [
    "Calories",
    "Total Fat (g)",
    "Total Sugars (g)",
    "Carbohydrates (Carbs) (g)",
    "Protein (g)",
]

def main():
    # ----------------------------
    # 1) Load, select, scale
    # ----------------------------
    df = pd.read_csv(PROCESSED_PATH)
    data = df[FEATURES].apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data)

    # ----------------------------
    # 2) PCA to 2D (class style)
    # ----------------------------
    pca = PCA(n_components=2, random_state=42)
    pca_data = pca.fit_transform(scaled_data)

    plt.figure(figsize=(7,6))
    plt.scatter(pca_data[:, 0], pca_data[:, 1], alpha=0.7, edgecolor="k", s=20)
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.title("PCA-reduced Data")
    plt.tight_layout()
    pca_scatter_path = os.path.join(OUTPUT_DIR, "pca_scatter.png")
    plt.savefig(pca_scatter_path, dpi=200)
    plt.close()

    # ----------------------------
    # 3) Elbow + Silhouette on PCA data (k=2..10)
    # ----------------------------
    k_values = range(2, 11)
    inertia = []
    silhouette_scores = []

    for k in k_values:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pca_data)
        inertia.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(pca_data, kmeans.labels_))

    # Elbow
    plt.figure(figsize=(7,5))
    plt.plot(k_values, inertia, marker="o")
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Inertia")
    plt.title("Elbow Method for Optimal k")
    plt.tight_layout()
    elbow_path = os.path.join(OUTPUT_DIR, "elbow.png")
    plt.savefig(elbow_path, dpi=200)
    plt.close()

    # Silhouette
    plt.figure(figsize=(7,5))
    plt.plot(k_values, silhouette_scores, marker="o", color="orange")
    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Silhouette Score")
    plt.title("Silhouette Scores for Different k")
    plt.tight_layout()
    sil_path = os.path.join(OUTPUT_DIR, "silhouette.png")
    plt.savefig(sil_path, dpi=200)
    plt.close()

    # ----------------------------
    # 4) Choose k and fit KMeans on PCA data
    #     (set optimal_k explicitly to match your class demo if needed)
    # ----------------------------
    # If you want to force k=10 like the class figure, set: optimal_k = 10
    optimal_k = int(k_values[np.argmax(silhouette_scores)])  # auto-pick by silhouette
    # optimal_k = 10  # <-- uncomment to force k=10

    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    kmeans.fit(pca_data)
    data_with_clusters = data.copy()
    data_with_clusters["Cluster"] = kmeans.labels_

    # Colored PCA scatter
    plt.figure(figsize=(8,6))
    sc = plt.scatter(pca_data[:, 0], pca_data[:, 1],
                     c=kmeans.labels_, cmap="viridis", alpha=0.7, edgecolor="k", s=20)
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.title(f"K-means Clustering with {optimal_k} Clusters (PCA-reduced Data)")
    plt.colorbar(sc, label="Cluster")
    plt.tight_layout()
    kmeans_pca_path = os.path.join(OUTPUT_DIR, f"kmeans_pca_clusters_k{optimal_k}.png")
    plt.savefig(kmeans_pca_path, dpi=200)
    plt.close()

    # ----------------------------
    # 5) Boxplots per feature by cluster (class style)
    # ----------------------------
    sns.set_theme()
    for feature in FEATURES:
        plt.figure(figsize=(8,6))
        sns.boxplot(x="Cluster", y=feature, data=data_with_clusters, palette="Set3")
        plt.title(f"Distribution of {feature} by Cluster")
        plt.xlabel("Cluster")
        plt.ylabel(feature)
        plt.tight_layout()
        bp_path = os.path.join(
            OUTPUT_DIR,
            f"box_{feature.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')}.png"
        )
        plt.savefig(bp_path, dpi=200)
        plt.close()

    # Save clustered dataset (optional but handy)
    out_csv = os.path.join(OUTPUT_DIR, "nutrition_with_clusters_kmeans_pca.csv")
    data_with_clusters.to_csv(out_csv, index=False)

    print("Saved:")
    print(f" - {pca_scatter_path}")
    print(f" - {elbow_path}")
    print(f" - {sil_path}")
    print(f" - {kmeans_pca_path}")
    print(f" - boxplots for all features in {OUTPUT_DIR}")
    print(f" - clustered CSV: {out_csv}")

if __name__ == "__main__":
    main()
