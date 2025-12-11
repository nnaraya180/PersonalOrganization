# """
# Train ML models to predict mood and energy from nutrition features.
# Saves two models: mood_model.pkl and energy_model.pkl
# """
# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import LabelEncoder
# import joblib

# DATA_PATH = "../Data/processed/nutrition_labels_clean.csv"
# MOOD_MODEL_PATH = "../backend/ml/mood_model.pkl"
# ENERGY_MODEL_PATH = "../backend/ml/energy_model.pkl"

# # Load data
# df = pd.read_csv(DATA_PATH)

# # Features and targets
# FEATURES = [
#     "Calories",
#     "Total Fat (g)",
#     "Total Sugars (g)",
#     "Carbohydrates (Carbs) (g)",
#     "Protein (g)",
# ]

# # Encode mood and energy as ordinal labels
# mood_le = LabelEncoder()
# energy_le = LabelEncoder()
# df = df.dropna(subset=FEATURES + ["Mood", "Energy"])
# df["Mood_label"] = mood_le.fit_transform(df["Mood"].astype(str))
# df["Energy_label"] = energy_le.fit_transform(df["Energy"].astype(str))

# X = df[FEATURES]
# y_mood = df["Mood_label"]
# y_energy = df["Energy_label"]

# # Train/test split
# X_train, X_test, y_mood_train, y_mood_test, y_energy_train, y_energy_test = train_test_split(
#     X, y_mood, y_energy, test_size=0.2, random_state=42
# )

# # Train models
# mood_model = RandomForestRegressor(n_estimators=100, random_state=42)
# mood_model.fit(X_train, y_mood_train)
# energy_model = RandomForestRegressor(n_estimators=100, random_state=42)
# energy_model.fit(X_train, y_energy_train)

# # Save models and encoders
# joblib.dump(mood_model, MOOD_MODEL_PATH)
# joblib.dump(energy_model, ENERGY_MODEL_PATH)
# joblib.dump(mood_le, "../backend/ml/mood_label_encoder.pkl")
# joblib.dump(energy_le, "../backend/ml/energy_label_encoder.pkl")

# print("Models and encoders saved.")

"""
Enhanced ML training for mood and energy prediction from nutrition data.
Includes feature engineering, proper validation, and model comparison.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PATH = "../Data/processed/nutrition_labels_clean.csv"
MODEL_DIR = "../backend/ml/"

class NutritionFeatureEngineering:
    """Create meaningful derived features from raw nutrition data."""
    
    @staticmethod
    def engineer_features(df):
        """Add engineered features based on nutrition science."""
        df = df.copy()
        
        # Prevent division by zero
        eps = 1e-6
        
        # Macronutrient ratios (important for energy/mood)
        df['protein_to_carb_ratio'] = df['Protein (g)'] / (df['Carbohydrates (Carbs) (g)'] + eps)
        df['fat_to_carb_ratio'] = df['Total Fat (g)'] / (df['Carbohydrates (Carbs) (g)'] + eps)
        df['protein_pct'] = (df['Protein (g)'] * 4) / (df['Calories'] + eps)
        df['carb_pct'] = (df['Carbohydrates (Carbs) (g)'] * 4) / (df['Calories'] + eps)
        df['fat_pct'] = (df['Total Fat (g)'] * 9) / (df['Calories'] + eps)
        
        # Sugar metrics (high sugar -> energy spike then crash)
        df['sugar_to_total_carb'] = df['Total Sugars (g)'] / (df['Carbohydrates (Carbs) (g)'] + eps)
        df['sugar_load'] = df['Total Sugars (g)'] * df['Carbohydrates (Carbs) (g)']
        
        # Caloric density (calories per gram - assumes 100g serving)
        # Higher density foods may affect satiety/mood differently
        df['caloric_density'] = df['Calories'] / 100.0
        
        # Protein power score (protein is associated with satiety and stable mood)
        df['protein_score'] = df['Protein (g)'] * df['protein_pct']
        
        return df

def prepare_data(df, feature_cols):
    """Clean and prepare data for modeling."""
    # Remove rows with missing values
    df = df.dropna(subset=feature_cols + ["Mood", "Energy"])
    
    # Encode target variables
    mood_le = LabelEncoder()
    energy_le = LabelEncoder()
    
    df["Mood_label"] = mood_le.fit_transform(df["Mood"].astype(str))
    df["Energy_label"] = energy_le.fit_transform(df["Energy"].astype(str))
    
    return df, mood_le, energy_le

def evaluate_model(model, X_train, X_test, y_train, y_test, label_encoder):
    """Comprehensive model evaluation."""
    # Train
    model.fit(X_train, y_train)
    
    # Predict
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    # Round and clip predictions to valid label range
    train_pred = np.clip(np.round(train_pred).astype(int), 0, len(label_encoder.classes_) - 1)
    test_pred = np.clip(np.round(test_pred).astype(int), 0, len(label_encoder.classes_) - 1)
    
    # Metrics
    train_mae = mean_absolute_error(y_train, train_pred)
    test_mae = mean_absolute_error(y_test, test_pred)
    train_r2 = r2_score(y_train, train_pred)
    test_r2 = r2_score(y_test, test_pred)
    
    # Cross-validation score
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, 
                                 scoring='neg_mean_absolute_error')
    cv_mae = -cv_scores.mean()
    
    return {
        'train_mae': train_mae,
        'test_mae': test_mae,
        'train_r2': train_r2,
        'test_r2': test_r2,
        'cv_mae': cv_mae,
        'model': model
    }

def train_and_select_best_model(X_train, X_test, y_train, y_test, label_encoder, target_name):
    """Train multiple models and select the best one."""
    models = {
        'RandomForest': RandomForestRegressor(n_estimators=200, max_depth=10, 
                                              min_samples_split=10, random_state=42),
        'GradientBoosting': GradientBoostingRegressor(n_estimators=200, max_depth=5,
                                                      learning_rate=0.1, random_state=42),
        'Ridge': Ridge(alpha=1.0)
    }
    
    print(f"\n{'='*60}")
    print(f"Training models for {target_name}")
    print(f"{'='*60}")
    
    results = {}
    for name, model in models.items():
        print(f"\nEvaluating {name}...")
        results[name] = evaluate_model(model, X_train, X_test, y_train, y_test, label_encoder)
        
        print(f"  Train MAE: {results[name]['train_mae']:.4f}")
        print(f"  Test MAE:  {results[name]['test_mae']:.4f}")
        print(f"  CV MAE:    {results[name]['cv_mae']:.4f}")
        print(f"  Test R²:   {results[name]['test_r2']:.4f}")
    
    # Select best model based on test MAE
    best_model_name = min(results.keys(), key=lambda k: results[k]['test_mae'])
    print(f"\n✓ Best model: {best_model_name}")
    
    return results[best_model_name]['model'], results

def main():
    # Load data
    print("Loading data...")
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows")
    
    # Basic features
    BASE_FEATURES = [
        "Calories",
        "Total Fat (g)",
        "Total Sugars (g)",
        "Carbohydrates (Carbs) (g)",
        "Protein (g)",
    ]
    
    # Engineer features
    print("\nEngineering features...")
    df = NutritionFeatureEngineering.engineer_features(df)
    
    # All features (base + engineered)
    ENGINEERED_FEATURES = [
        'protein_to_carb_ratio', 'fat_to_carb_ratio', 
        'protein_pct', 'carb_pct', 'fat_pct',
        'sugar_to_total_carb', 'sugar_load', 
        'caloric_density', 'protein_score'
    ]
    ALL_FEATURES = BASE_FEATURES + ENGINEERED_FEATURES
    
    # Prepare data
    df, mood_le, energy_le = prepare_data(df, ALL_FEATURES)
    print(f"Clean data: {len(df)} rows")
    print(f"Mood classes: {list(mood_le.classes_)}")
    print(f"Energy classes: {list(energy_le.classes_)}")
    
    X = df[ALL_FEATURES]
    y_mood = df["Mood_label"]
    y_energy = df["Energy_label"]
    
    # Optional: Scale features (helps some models)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=ALL_FEATURES, index=X.index)
    
    # Train/test split (stratified by mood to ensure balanced classes)
    X_train, X_test, y_mood_train, y_mood_test = train_test_split(
        X_scaled, y_mood, test_size=0.2, random_state=42, stratify=y_mood
    )
    _, _, y_energy_train, y_energy_test = train_test_split(
        X_scaled, y_energy, test_size=0.2, random_state=42, stratify=y_energy
    )
    
    # Train models
    print("\n" + "="*60)
    print("MOOD MODEL TRAINING")
    print("="*60)
    mood_model, mood_results = train_and_select_best_model(
        X_train, X_test, y_mood_train, y_mood_test, mood_le, "Mood"
    )
    
    print("\n" + "="*60)
    print("ENERGY MODEL TRAINING")
    print("="*60)
    energy_model, energy_results = train_and_select_best_model(
        X_train, X_test, y_energy_train, y_energy_test, energy_le, "Energy"
    )
    
    # Feature importance (if available)
    if hasattr(mood_model, 'feature_importances_'):
        print("\n" + "="*60)
        print("TOP 5 MOOD FEATURES")
        print("="*60)
        importances = pd.DataFrame({
            'feature': ALL_FEATURES,
            'importance': mood_model.feature_importances_
        }).sort_values('importance', ascending=False)
        print(importances.head())
    
    # Save everything
    print("\n" + "="*60)
    print("SAVING MODELS")
    print("="*60)
    joblib.dump(mood_model, MODEL_DIR + "mood_model.pkl")
    joblib.dump(energy_model, MODEL_DIR + "energy_model.pkl")
    joblib.dump(mood_le, MODEL_DIR + "mood_label_encoder.pkl")
    joblib.dump(energy_le, MODEL_DIR + "energy_label_encoder.pkl")
    joblib.dump(scaler, MODEL_DIR + "feature_scaler.pkl")
    
    # Save feature names for inference
    joblib.dump(ALL_FEATURES, MODEL_DIR + "feature_names.pkl")
    
    print("✓ Models saved successfully")
    print(f"  - mood_model.pkl (Test MAE: {mood_results[list(mood_results.keys())[0]]['test_mae']:.4f})")
    print(f"  - energy_model.pkl (Test MAE: {energy_results[list(energy_results.keys())[0]]['test_mae']:.4f})")
    print(f"  - Label encoders and scaler saved")

if __name__ == "__main__":
    main()