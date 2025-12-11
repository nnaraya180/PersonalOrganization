# ML Integration Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      main.py                               │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ Existing Routers:                                    │  │ │
│  │  │  • chat_router (/chat/*)                            │  │ │
│  │  │  • other_routers (...)                              │  │ │
│  │  ├──────────────────────────────────────────────────────┤  │ │
│  │  │ ✨ NEW: ML Router (/api/ml/*)                       │  │ │
│  │  │  • POST /predict-mood-energy                        │  │ │
│  │  │  • POST /import-recipe                              │  │ │
│  │  │  • GET  /health                                     │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           routers/ml_predictions.py                        │ │
│  │                                                             │ │
│  │  Handles requests, normalizes input, returns responses    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              ml/nutrition_import.py                        │ │
│  │                                                             │ │
│  │  Multi-format nutrition data parser:                      │ │
│  │  • Generic JSON                                           │ │
│  │  • Spoonacular API                                        │ │
│  │  • Edamam API                                             │ │
│  │  • USDA FoodData Central                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         ml/mood_energy_model.py                           │ │
│  │                                                             │
│  │  Core ML Engine:                                          │ │
│  │  1. estimate_missing_macros() - Fill missing data        │ │
│  │  2. engineer_features()      - Create 14 features        │ │
│  │  3. predict_mood_effect()    - Get mood prediction       │ │
│  │  4. predict_energy_effect()  - Get energy prediction     │ │
│  │  5. predict_both()           - Combined prediction       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Trained Models                          │ │
│  │                                                             │ │
│  │  mood_model.pkl         - RandomForest (98.99% acc.)    │ │
│  │  energy_model.pkl       - Ridge Regression (88.75% acc.)│ │
│  │  feature_scaler.pkl     - StandardScaler                │ │
│  │  feature_names.pkl      - Feature ordering              │ │
│  │  *_label_encoder.pkl    - Label encoders                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### Scenario 1: Direct Nutrition Data
```
Client Request
    ↓
{
  "nutrition": {
    "calories": 450,
    "protein_g": 25,
    "carbs_g": 50,
    "fat_g": 15
  }
}
    ↓
ml_predictions.py
    ↓
predict_both(nutrition)
    ↓
mood_energy_model.py
  1. Check if data complete
  2. Engineer features (if complete)
  3. Scale features
  4. Predict with models
    ↓
Response
{
  "mood": {"label": "Neutral", "score": 0.5, ...},
  "energy": {"label": "Low", "score": 0.5, ...}
}
```

### Scenario 2: Partial Data (Only Calories)
```
Client Request
    ↓
{
  "nutrition": {
    "calories": 450
  }
}
    ↓
predict_both(nutrition)
    ↓
estimate_missing_macros()
{
  "calories": 450,
  "protein_g": 45,      ← estimated (20% of calories)
  "carbs_g": 112,       ← estimated (50% of calories)
  "fat_g": 15,          ← estimated (30% of calories)
  "sugar_g": 22         ← estimated (20% of carbs)
}
    ↓
engineer_features() → scale → predict
    ↓
Response with confidence: 0.2 (low, since mostly estimated)
```

### Scenario 3: External Recipe API
```
Client Request
    ↓
{
  "source": "spoonacular",
  "recipe_api_data": { ... }
}
    ↓
ml_predictions.py
    ↓
nutrition_import.py
    ↓
parse_recipe_nutrition("spoonacular", data)
    ↓
NutritionData object
{
  calories: 350,
  protein_g: 28,
  carbs_g: 12,
  fat_g: 22,
  sugar_g: None,
  fiber_g: None
}
    ↓
predict_both(nutrition)
  (estimates sugar_g and fiber_g)
    ↓
Response with nutrition + predictions + completeness metrics
```

## Feature Engineering Pipeline

```
Raw Nutrition Data
├─ Calories
├─ Protein (g)
├─ Carbs (g)
├─ Fat (g)
└─ Sugar (g)
    ↓
Engineered Features (9 additional)
├─ protein_to_carb_ratio
├─ fat_to_carb_ratio
├─ protein_pct
├─ carb_pct
├─ fat_pct
├─ sugar_to_total_carb
├─ sugar_load
├─ caloric_density
└─ protein_score
    ↓
Total: 14 Features
    ↓
StandardScaler normalization
    ↓
Model input (5+9 engineered)
```

## Model Architecture

### Mood Prediction
```
14 Features
    ↓
RandomForestRegressor
├─ n_estimators: 200
├─ max_depth: 10
├─ min_samples_split: 10
└─ random_state: 42
    ↓
Output: [0-2] (ordinal indices)
    ↓
Label Encoder
    ├─ 0 → "Happy"
    ├─ 1 → "Neutral"
    └─ 2 → "Sad"
    ↓
Normalized Score [0-1]
```

### Energy Prediction
```
14 Features
    ↓
RidgeRegressor
├─ alpha: 1.0
└─ random_state: 42
    ↓
Output: [0-2] (ordinal indices)
    ↓
Label Encoder
    ├─ 0 → "Energy Burst"
    ├─ 1 → "Low"
    └─ 2 → "Normal"
    ↓
Normalized Score [0-1]
```

## Confidence Scoring Logic

```
Data Completeness Check
├─ All fields present? → High confidence (100%)
├─ 80%+ fields present? → High confidence (80%+)
├─ 40-80% fields present? → Medium confidence (40-80%)
└─ <40% fields present? → Low confidence (<40%)
    ↓
Returned as confidence score in response
    ↓
Can be used to weight predictions in downstream logic
```

## Integration Points with Existing Backend

### Current: recipe_scoring.py
```
score_recipes(recipes, pantry, constraints)
  ├─ coverage_score         [0-1]
  ├─ expiring_score         [0-1]
  ├─ nutrition_score        [-1, 1]
  └─ mood_energy_score      [-1, 1]  (basic heuristics)
      ↓
  final_score = weighted sum
```

### Future: With ML Integration
```
score_recipes(recipes, pantry, constraints)
  ├─ coverage_score         [0-1]
  ├─ expiring_score         [0-1]
  ├─ nutrition_score        [-1, 1]
  └─ mood_energy_score      [-1, 1]  (✨ ML-based)
      ├─ mood_score         [0-1]  (RandomForest)
      └─ energy_score       [0-1]  (Ridge)
      ↓
  final_score = weighted sum
      ↓
  debug info includes:
    ├─ ml_confidence
    ├─ ml_data_quality
    ├─ predicted_mood_effect
    └─ predicted_energy_effect
```

## Request/Response Flow

### Predict Mood & Energy
```
POST /api/ml/predict-mood-energy

Request:
{
  "nutrition": {
    "calories": 450,
    "protein_g": 25,
    "carbs_g": 50,
    "fat_g": 15,
    "sugar_g": 8
  }
}

Processing:
1. Validate input (minimum calories required)
2. Engineer features
3. Scale features
4. Predict with both models
5. Post-process predictions
6. Calculate confidence

Response:
{
  "mood": {
    "label": "Neutral",
    "label_index": 1,
    "score": 0.5,
    "confidence": 1.0,
    "estimated_fields": [],
    "data_quality": "high"
  },
  "energy": {
    "label": "Low",
    "label_index": 1,
    "score": 0.5,
    "confidence": 1.0,
    "estimated_fields": [],
    "data_quality": "high"
  }
}
```

### Import Recipe
```
POST /api/ml/import-recipe

Request:
{
  "source": "generic",
  "recipe_data": {
    "name": "Chicken Salad",
    "calories": 350,
    "protein": 28,
    "carbs": 12,
    "fat": 22
  }
}

Processing:
1. Parse nutrition based on source format
2. Estimate missing fields
3. Predict mood and energy
4. Calculate completeness metrics

Response:
{
  "nutrition": {
    "calories": 350,
    "protein_g": 28,
    "carbs_g": 12,
    "fat_g": 22,
    "sugar_g": 2.4,
    "fiber_g": 1.2
  },
  "completeness": 0.667,
  "missing_fields": ["sugar_g", "fiber_g"],
  "predictions": {
    "mood": { ... },
    "energy": { ... }
  }
}
```

## Performance Metrics

```
Mood Model:
├─ Training Accuracy: 98.99%
├─ Test MAE: 0.0464
├─ Cross-Validation MAE: 0.0623
└─ Top Feature: Total Sugars (79.1% importance)

Energy Model:
├─ Training Accuracy: 88.75%
├─ Test MAE: 0.6424
├─ Cross-Validation MAE: 0.6347
└─ Model Type: Ridge Regression (selected over RandomForest/GradientBoosting)

Data:
├─ Training samples: 80,000
├─ Test samples: 20,000
└─ Features: 14 (5 base + 9 engineered)
```

## Error Handling

```
Request
    ↓
Validation
├─ Missing required fields?
│   └─ Return 400: "Must provide nutrition or recipe_api_data"
├─ Insufficient data?
│   └─ Return 400: "Insufficient nutrition data"
└─ Valid?
    ↓
    Processing
    ├─ Model load failure?
    │   └─ Return 503: "ML service unavailable"
    └─ Success?
        ↓
        Return 200: Predictions
```

## Files and Responsibilities

```
frontend/
└─ Makes requests to API

backend/
├─ main.py
│   └─ Registers all routers including ml_router
├─ routers/
│   ├─ chat.py (existing)
│   └─ ml_predictions.py (NEW)
│       └─ 3 endpoints: predict-mood-energy, import-recipe, health
└─ ml/
    ├─ mood_energy_model.py (NEW)
    │   ├─ predict_mood_effect()
    │   ├─ predict_energy_effect()
    │   └─ predict_both()
    ├─ nutrition_import.py (NEW)
    │   ├─ NutritionData class
    │   ├─ RecipeNutritionExtractor
    │   └─ parse_recipe_nutrition()
    └─ *.pkl files (trained models & preprocessing)

analysis/
├─ train_mood_energy_model.py (UPDATED)
└─ eval_mood_energy_model.py (NEW)
```

---

This architecture provides a clean separation of concerns:
- **API Layer** handles HTTP/request validation
- **Parsing Layer** handles multi-format extraction
- **ML Layer** handles prediction logic
- **Models** are persisted and loaded on-demand

The system is designed to be:
- ✅ Modular (easy to swap models)
- ✅ Testable (each layer can be tested independently)
- ✅ Scalable (can add caching, batching, etc.)
- ✅ Maintainable (clear responsibilities)
