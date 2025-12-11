# """
# backend/ml/mood_energy_model.py
# Mood & Energy prediction helpers for recipe nutrition profiles.

# This is a placeholder model using simple heuristics based on macro nutrients.
# TODO: Replace with trained ML model when available.
# """

# from typing import Optional, Dict
# import os
# import joblib
# import numpy as np

# MACRO_KEYS = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]

# # Model/encoder paths (relative to this file)
# MODEL_DIR = os.path.dirname(__file__)
# MOOD_MODEL_PATH = os.path.join(MODEL_DIR, "mood_model.pkl")
# ENERGY_MODEL_PATH = os.path.join(MODEL_DIR, "energy_model.pkl")
# MOOD_LE_PATH = os.path.join(MODEL_DIR, "mood_label_encoder.pkl")
# ENERGY_LE_PATH = os.path.join(MODEL_DIR, "energy_label_encoder.pkl")

# # Lazy load models/encoders
# _mood_model = None
# _energy_model = None
# _mood_le = None
# _energy_le = None

# def _load_models():
#     global _mood_model, _energy_model, _mood_le, _energy_le
#     if _mood_model is None:
#         _mood_model = joblib.load(MOOD_MODEL_PATH)
#     if _energy_model is None:
#         _energy_model = joblib.load(ENERGY_MODEL_PATH)
#     if _mood_le is None:
#         _mood_le = joblib.load(MOOD_LE_PATH)
#     if _energy_le is None:
#         _energy_le = joblib.load(ENERGY_LE_PATH)

# def _features_to_array(features: Dict[str, float]) -> np.ndarray:
#     arr = [features.get("calories", 0),
#            features.get("fat_g", 0),
#            features.get("carbs_g", 0),
#            features.get("protein_g", 0),
#            features.get("fiber_g", 0)]
#     return np.array(arr).reshape(1, -1)



# def predict_mood_effect(features: Dict[str, float]) -> Optional[float]:
#     """
#     Given macro features for a meal, return a scalar for predicted mood effect (ordinal label).
#     Returns a float label (higher = more positive mood). None if insufficient data.
#     """
#     if not features or sum([features.get(k, 0) is not None for k in MACRO_KEYS]) < 3:
#         return None
#     _load_models()
#     arr = _features_to_array(features)
#     pred = _mood_model.predict(arr)[0]
#     return float(pred)



# def predict_energy_effect(features: Dict[str, float]) -> Optional[float]:
#     """
#     Given macro features for a meal, return a scalar for predicted energy effect (ordinal label).
#     Returns a float label (higher = more energy). None if insufficient data.
#     """
#     if not features or sum([features.get(k, 0) is not None for k in MACRO_KEYS]) < 3:
#         return None
#     _load_models()
#     arr = _features_to_array(features)
#     pred = _energy_model.predict(arr)[0]
#     return float(pred)

# # TODO: Replace with trained model loading and prediction when available.

"""
backend/ml/mood_energy_model.py
Mood & Energy prediction with feature engineering and proper model loading.
"""
"""
backend/ml/mood_energy_model.py
Robust mood & energy prediction that handles incomplete nutritional data.
"""
from typing import Optional, Dict, Tuple, List
import os
import joblib
import numpy as np
import pandas as pd
import warnings

MODEL_DIR = os.path.dirname(__file__)

# Model paths
MOOD_MODEL_PATH = os.path.join(MODEL_DIR, "mood_model.pkl")
ENERGY_MODEL_PATH = os.path.join(MODEL_DIR, "energy_model.pkl")
MOOD_LE_PATH = os.path.join(MODEL_DIR, "mood_label_encoder.pkl")
ENERGY_LE_PATH = os.path.join(MODEL_DIR, "energy_label_encoder.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.pkl")
FEATURE_NAMES_PATH = os.path.join(MODEL_DIR, "feature_names.pkl")

# Lazy load
_mood_model = None
_energy_model = None
_mood_le = None
_energy_le = None
_scaler = None
_feature_names = None

# Reasonable defaults based on USDA averages
NUTRITIONAL_DEFAULTS = {
    'calories': 200,      # Moderate meal
    'protein_g': 10,      # ~20% of calories
    'carbs_g': 25,        # ~50% of calories
    'fat_g': 7,           # ~30% of calories
    'sugar_g': 5,         # ~20% of carbs
    'fiber_g': 3          # Moderate fiber
}

# Minimum data requirements for prediction
MIN_REQUIRED_FIELDS = ['calories']  # At minimum, we need calories

def _load_models():
    """Lazy load all models and preprocessing objects."""
    global _mood_model, _energy_model, _mood_le, _energy_le, _scaler, _feature_names
    
    if _mood_model is None:
        _mood_model = joblib.load(MOOD_MODEL_PATH)
    if _energy_model is None:
        _energy_model = joblib.load(ENERGY_MODEL_PATH)
    if _mood_le is None:
        _mood_le = joblib.load(MOOD_LE_PATH)
    if _energy_le is None:
        _energy_le = joblib.load(ENERGY_LE_PATH)
    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)
    if _feature_names is None:
        _feature_names = joblib.load(FEATURE_NAMES_PATH)

def estimate_missing_macros(nutrition_data: Dict[str, float]) -> Dict[str, float]:
    """
    Intelligently estimate missing macronutrients based on available data.
    Uses nutritional relationships and typical ratios.
    
    Args:
        nutrition_data: Partial nutrition data
    
    Returns:
        Complete nutrition data with estimated values
    """
    data = nutrition_data.copy()
    
    # If we have calories but no macros, estimate based on typical ratios
    if 'calories' in data and data['calories'] > 0:
        calories = data['calories']
        
        # Estimate protein (20% of calories, 4 cal/g)
        if 'protein_g' not in data or data['protein_g'] is None:
            data['protein_g'] = (calories * 0.20) / 4
        
        # Estimate carbs (50% of calories, 4 cal/g)
        if 'carbs_g' not in data or data['carbs_g'] is None:
            data['carbs_g'] = (calories * 0.50) / 4
        
        # Estimate fat (30% of calories, 9 cal/g)
        if 'fat_g' not in data or data['fat_g'] is None:
            data['fat_g'] = (calories * 0.30) / 9
    
    # If we have macros but no calories, calculate it
    elif all(k in data for k in ['protein_g', 'carbs_g', 'fat_g']):
        if 'calories' not in data or data['calories'] is None:
            data['calories'] = (
                data['protein_g'] * 4 +
                data['carbs_g'] * 4 +
                data['fat_g'] * 9
            )
    
    # Estimate sugar as ~20% of carbs if missing
    if 'sugar_g' not in data or data['sugar_g'] is None:
        if 'carbs_g' in data and data['carbs_g'] is not None:
            data['sugar_g'] = data['carbs_g'] * 0.20
        else:
            data['sugar_g'] = NUTRITIONAL_DEFAULTS['sugar_g']
    
    # Estimate fiber if missing
    if 'fiber_g' not in data or data['fiber_g'] is None:
        if 'carbs_g' in data and data['carbs_g'] is not None:
            data['fiber_g'] = data['carbs_g'] * 0.10  # ~10% of carbs
        else:
            data['fiber_g'] = NUTRITIONAL_DEFAULTS['fiber_g']
    
    # Fill any remaining missing values with defaults
    for key, default_value in NUTRITIONAL_DEFAULTS.items():
        if key not in data or data[key] is None:
            data[key] = default_value
    
    return data

def get_data_quality_score(nutrition_data: Dict[str, float]) -> float:
    """
    Calculate a quality score (0-1) based on how much real data we have.
    
    Returns:
        Float between 0 (all estimated) and 1 (all real data)
    """
    important_fields = ['calories', 'protein_g', 'carbs_g', 'fat_g', 'sugar_g']
    
    present_count = sum(
        1 for field in important_fields 
        if field in nutrition_data and nutrition_data[field] is not None
    )
    
    return present_count / len(important_fields)

def engineer_features(nutrition_data: Dict[str, float]) -> Dict[str, float]:
    """
    Create engineered features from nutrition data.
    Handles missing values gracefully by estimating them first.
    
    Args:
        nutrition_data: Dict with keys like 'calories', 'protein_g', 'carbs_g', etc.
                       Can have missing values.
    
    Returns:
        Dict with all features (base + engineered)
    """
    # First, estimate any missing values
    complete_data = estimate_missing_macros(nutrition_data)
    
    eps = 1e-6
    
    # Extract values
    calories = complete_data['calories']
    protein = complete_data['protein_g']
    carbs = complete_data['carbs_g']
    fat = complete_data['fat_g']
    sugar = complete_data['sugar_g']
    
    # Base features (match training column names)
    features = {
        'Calories': calories,
        'Total Fat (g)': fat,
        'Total Sugars (g)': sugar,
        'Carbohydrates (Carbs) (g)': carbs,
        'Protein (g)': protein,
    }
    
    # Engineered features
    features['protein_to_carb_ratio'] = protein / (carbs + eps)
    features['fat_to_carb_ratio'] = fat / (carbs + eps)
    features['protein_pct'] = (protein * 4) / (calories + eps)
    features['carb_pct'] = (carbs * 4) / (calories + eps)
    features['fat_pct'] = (fat * 9) / (calories + eps)
    features['sugar_to_total_carb'] = sugar / (carbs + eps)
    features['sugar_load'] = sugar * carbs
    features['caloric_density'] = calories / 100.0
    features['protein_score'] = protein * features['protein_pct']
    
    return features

def _prepare_features(nutrition_data: Dict[str, float]) -> np.ndarray:
    """Convert nutrition dict to feature array for model input."""
    # Engineer features (handles missing data internally)
    features = engineer_features(nutrition_data)
    
    # Load models to get feature names
    _load_models()
    
    # Create array in correct order
    feature_array = np.array([features.get(name, 0) for name in _feature_names])
    
    # Scale features
    feature_array = _scaler.transform(feature_array.reshape(1, -1))
    
    return feature_array

def predict_mood_effect(nutrition_data: Dict[str, float]) -> Optional[Dict[str, any]]:
    """
    Predict mood effect from nutrition data.
    Handles incomplete data by estimating missing values.
    
    Args:
        nutrition_data: Dict with any combination of 'calories', 'protein_g', 
                       'carbs_g', 'fat_g', 'sugar_g', 'fiber_g'
    
    Returns:
        Dict with:
          - 'label' (str): mood category
          - 'score' (float 0-1): normalized score
          - 'label_index' (int): ordinal index
          - 'confidence' (float 0-1): based on data quality
          - 'estimated_fields' (list): which fields were estimated
        or None if prediction fails
    """
    # Check minimum requirements
    if not nutrition_data or not any(k in nutrition_data for k in MIN_REQUIRED_FIELDS):
        return None
    
    try:
        _load_models()
        
        # Track which fields we estimated
        original_fields = set(k for k, v in nutrition_data.items() if v is not None)
        
        # Prepare features (handles missing data)
        X = _prepare_features(nutrition_data)
        
        # Calculate data quality
        quality_score = get_data_quality_score(nutrition_data)
        
        # Track estimated fields
        all_fields = {'calories', 'protein_g', 'carbs_g', 'fat_g', 'sugar_g'}
        estimated_fields = list(all_fields - original_fields)
        
        # Predict
        raw_pred = _mood_model.predict(X)[0]
        label_idx = int(np.clip(np.round(raw_pred), 0, len(_mood_le.classes_) - 1))
        label = _mood_le.classes_[label_idx]
        
        # Normalize score to 0-1
        score = label_idx / (len(_mood_le.classes_) - 1) if len(_mood_le.classes_) > 1 else 0.5
        
        return {
            'label': label,
            'label_index': label_idx,
            'score': score,
            'confidence': quality_score,
            'estimated_fields': estimated_fields,
            'data_quality': 'high' if quality_score > 0.8 else 'medium' if quality_score > 0.4 else 'low'
        }
    except Exception as e:
        print(f"Error predicting mood: {e}")
        return None

def predict_energy_effect(nutrition_data: Dict[str, float]) -> Optional[Dict[str, any]]:
    """
    Predict energy effect from nutrition data.
    Handles incomplete data by estimating missing values.
    
    Args:
        nutrition_data: Dict with any combination of 'calories', 'protein_g', 
                       'carbs_g', 'fat_g', 'sugar_g', 'fiber_g'
    
    Returns:
        Dict with:
          - 'label' (str): energy category
          - 'score' (float 0-1): normalized score
          - 'label_index' (int): ordinal index
          - 'confidence' (float 0-1): based on data quality
          - 'estimated_fields' (list): which fields were estimated
        or None if prediction fails
    """
    # Check minimum requirements
    if not nutrition_data or not any(k in nutrition_data for k in MIN_REQUIRED_FIELDS):
        return None
    
    try:
        _load_models()
        
        # Track which fields we estimated
        original_fields = set(k for k, v in nutrition_data.items() if v is not None)
        
        # Prepare features (handles missing data)
        X = _prepare_features(nutrition_data)
        
        # Calculate data quality
        quality_score = get_data_quality_score(nutrition_data)
        
        # Track estimated fields
        all_fields = {'calories', 'protein_g', 'carbs_g', 'fat_g', 'sugar_g'}
        estimated_fields = list(all_fields - original_fields)
        
        # Predict
        raw_pred = _energy_model.predict(X)[0]
        label_idx = int(np.clip(np.round(raw_pred), 0, len(_energy_le.classes_) - 1))
        label = _energy_le.classes_[label_idx]
        
        # Normalize score to 0-1
        score = label_idx / (len(_energy_le.classes_) - 1) if len(_energy_le.classes_) > 1 else 0.5
        
        return {
            'label': label,
            'label_index': label_idx,
            'score': score,
            'confidence': quality_score,
            'estimated_fields': estimated_fields,
            'data_quality': 'high' if quality_score > 0.8 else 'medium' if quality_score > 0.4 else 'low'
        }
    except Exception as e:
        print(f"Error predicting energy: {e}")
        return None

def predict_both(nutrition_data: Dict[str, float]) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Predict both mood and energy effects.
    
    Returns:
        Tuple of (mood_result, energy_result)
    """
    return (
        predict_mood_effect(nutrition_data),
        predict_energy_effect(nutrition_data)
    )

# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("TESTING MISSING DATA HANDLING")
    print("=" * 60)
    
    # Test case 1: Complete data
    print("\n1. Complete nutrition data:")
    complete = {
        'calories': 450,
        'protein_g': 25,
        'carbs_g': 50,
        'fat_g': 15,
        'sugar_g': 8
    }
    mood, energy = predict_both(complete)
    print(f"   Mood: {mood['label']} (confidence: {mood['confidence']:.2f})")
    print(f"   Energy: {energy['label']} (confidence: {energy['confidence']:.2f})")
    
    # Test case 2: Only calories
    print("\n2. Only calories available:")
    calories_only = {'calories': 450}
    mood, energy = predict_both(calories_only)
    print(f"   Mood: {mood['label']} (confidence: {mood['confidence']:.2f})")
    print(f"   Estimated: {mood['estimated_fields']}")
    print(f"   Data quality: {mood['data_quality']}")
    
    # Test case 3: Calories + protein
    print("\n3. Calories and protein only:")
    partial = {'calories': 450, 'protein_g': 25}
    mood, energy = predict_both(partial)
    print(f"   Mood: {mood['label']} (confidence: {mood['confidence']:.2f})")
    print(f"   Estimated: {mood['estimated_fields']}")
    
    # Test case 4: Macros but no calories
    print("\n4. Macros but no calories:")
    macros_only = {'protein_g': 25, 'carbs_g': 50, 'fat_g': 15}
    mood, energy = predict_both(macros_only)
    print(f"   Mood: {mood['label']} (confidence: {mood['confidence']:.2f})")
    print(f"   Estimated: {mood['estimated_fields']}")
    
    # Test case 5: Really sparse data
    print("\n5. Very sparse data (only protein):")
    sparse = {'protein_g': 25}
    mood, energy = predict_both(sparse)
    print(f"   Mood: {mood['label']} (confidence: {mood['confidence']:.2f})")
    print(f"   Data quality: {mood['data_quality']}")
    print(f"   Estimated: {mood['estimated_fields']}")