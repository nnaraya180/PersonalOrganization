# ML-Powered Recipe Recommendation Flow

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                │
│  POST /chat/recipes                                                 │
│  { "mood": "comfort", "energy": "high", "diet": "vegetarian" }     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PARSE CONSTRAINTS                                │
│  • mood = "comfort"                                                 │
│  • energy_level = "high"                                            │
│  • diet_types = ["vegetarian"]                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LOAD DATA FROM DATABASE                           │
│  • Recipes: SELECT * FROM recipe                                    │
│  • Pantry: SELECT * FROM item                                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               FILTER RECIPES (Hard Constraints)                     │
│  ✓ Time: <= max_time_minutes                                        │
│  ✓ Diet: matches diet_types                                         │
│  ✓ Include: has required ingredients                                │
│  ✓ Exclude: avoids excluded ingredients                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              SCORE EACH RECIPE (Soft Scoring)                       │
│                                                                     │
│  For each passing recipe:                                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ 1. COVERAGE SCORE (30%)                                  │      │
│  │    What % of ingredients are in pantry?                  │      │
│  │    have_count / total_ingredients                        │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ 2. EXPIRING SCORE (25%)                                  │      │
│  │    Uses expiring pantry items?                           │      │
│  │    Urgent (0-7 days): 1.0 weight                         │      │
│  │    Soon (7-14 days): 0.5 weight                          │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ 3. NUTRITION SCORE (20%)                                 │      │
│  │    Matches nutrition goal?                               │      │
│  │    • high_protein: >= 30g                                │      │
│  │    • low_carb: <= 35g                                    │      │
│  │    • low_calorie: <= 550 cal                             │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ 4. MOOD/ENERGY SCORE (25%) ⭐ ML POWERED! ⭐             │      │
│  │                                                          │      │
│  │  ┌────────────────────────────────────────────┐         │      │
│  │  │ Extract Nutrition Data                     │         │      │
│  │  │   calories, protein_g, carbs_g,            │         │      │
│  │  │   fat_g, sugar_g                           │         │      │
│  │  └─────────────────┬──────────────────────────┘         │      │
│  │                    │                                     │      │
│  │                    ▼                                     │      │
│  │  ┌────────────────────────────────────────────┐         │      │
│  │  │ Call ML Models                             │         │      │
│  │  │   mood_result, energy_result =             │         │      │
│  │  │     predict_both(nutrition_data)           │         │      │
│  │  └─────────────────┬──────────────────────────┘         │      │
│  │                    │                                     │      │
│  │                    ▼                                     │      │
│  │  ┌────────────────────────────────────────────┐         │      │
│  │  │ ML Predictions:                            │         │      │
│  │  │   mood_result = {                          │         │      │
│  │  │     "label": "Happy",                      │         │      │
│  │  │     "score": 1.8,                          │         │      │
│  │  │     "confidence": 0.95,                    │         │      │
│  │  │     "data_quality": "high"                 │         │      │
│  │  │   }                                        │         │      │
│  │  │   energy_result = {                        │         │      │
│  │  │     "label": "Energy Burst",               │         │      │
│  │  │     "score": 2.1,                          │         │      │
│  │  │     "confidence": 0.88,                    │         │      │
│  │  │     "data_quality": "high"                 │         │      │
│  │  │   }                                        │         │      │
│  │  └─────────────────┬──────────────────────────┘         │      │
│  │                    │                                     │      │
│  │                    ▼                                     │      │
│  │  ┌────────────────────────────────────────────┐         │      │
│  │  │ Map to User Request                        │         │      │
│  │  │                                            │         │      │
│  │  │   User wants: "high energy"                │         │      │
│  │  │   ML predicts: "Energy Burst" (88% conf)   │         │      │
│  │  │   → Score += 0.5 × 0.88 = +0.44            │         │      │
│  │  │                                            │         │      │
│  │  │   User wants: "comfort" mood               │         │      │
│  │  │   ML predicts: "Happy" (95% conf)          │         │      │
│  │  │   → Score += 0.5 × 0.95 = +0.475           │         │      │
│  │  │                                            │         │      │
│  │  │   Total ML score: 0.915                    │         │      │
│  │  │   Clamp to [-1, 1]: 0.915                  │         │      │
│  │  └────────────────────────────────────────────┘         │      │
│  │                                                          │      │
│  │  ⚠️  Fallback: If ML fails or no nutrition data,        │      │
│  │      use heuristics (old logic)                         │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │ FINAL SCORE = Weighted Sum                              │      │
│  │                                                          │      │
│  │   0.30 × coverage                                        │      │
│  │ + 0.25 × expiring                                        │      │
│  │ + 0.20 × nutrition                                       │      │
│  │ + 0.25 × mood_energy  ← ML powered!                      │      │
│  │ ─────────────────────                                    │      │
│  │ = final_score                                            │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  SORT BY FINAL SCORE (DESC)                         │
│  1. Recipe A (score: 0.85)                                          │
│  2. Recipe B (score: 0.72)                                          │
│  3. Recipe C (score: 0.68)                                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RETURN TOP K RECIPES                             │
│  [                                                                  │
│    {                                                                │
│      "recipe_id": 123,                                              │
│      "title": "High Protein Bowl",                                  │
│      "score": 0.85,                                                 │
│      "reason": "has 90% ingredients, uses expiring, fits goal",     │
│      "debug": {                                                     │
│        "coverage": {"score": 0.90},                                 │
│        "expiring": {"score": 0.33},                                 │
│        "nutrition": {"score": 1.0},                                 │
│        "mood_energy": {                                             │
│          "score": 0.915,                                            │
│          "ml_used": true,                                           │
│          "ml_mood": {"label": "Happy", "confidence": 0.95},         │
│          "ml_energy": {"label": "Energy Burst", "conf": 0.88}       │
│        }                                                            │
│      }                                                              │
│    }                                                                │
│  ]                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ML Model Details

### Training Data
- **Source**: `Data/processed/nutrition_labels_clean.csv`
- **Samples**: 100,000+
- **Features**: 14 engineered features from nutrition data
  - Base: calories, protein_g, carbs_g, fat_g, sugar_g
  - Engineered: protein_ratio, carb_ratio, fat_ratio, sugar_ratio, 
    calorie_density, protein_per_calorie, carb_per_calorie, 
    fat_per_calorie, sugar_per_calorie

### Models
1. **Mood Model**: RandomForest Regressor
   - Accuracy: 98.99%
   - Predicts: Happy (2), Neutral (1), Sad (0)
   
2. **Energy Model**: Ridge Regression
   - Accuracy: 88.75%
   - Predicts: Energy Burst (2), Normal (1), Low (0)

### Confidence Scoring
- **High confidence** (80-100%): Complete nutrition data
- **Medium confidence** (40-80%): Partial nutrition data
- **Low confidence** (0-40%): Minimal data (calories only)

---

## Integration Points

### 1. Import
```python
from ml.mood_energy_model import predict_both
```

### 2. Call in Scoring
```python
def compute_mood_energy_score(recipe, constraints):
    # Extract nutrition
    nutrition_data = {
        "calories": recipe.calories,
        "protein_g": recipe.protein_g,
        "carbs_g": recipe.carbs_g,
        "fat_g": recipe.fat_g,
        "sugar_g": recipe.nutrition_sugar_g
    }
    
    # Get ML predictions
    mood_result, energy_result = predict_both(nutrition_data)
    
    # Map to score based on user request
    score = map_ml_to_score(mood_result, energy_result, constraints)
    
    return score, explanation, debug
```

### 3. Weights
```python
SCORE_WEIGHTS = {
    "coverage": 0.30,
    "expiring": 0.25,
    "nutrition": 0.20,
    "mood_energy": 0.25  # Increased from 0.15!
}
```

---

## Testing

Run comprehensive tests:
```bash
cd backend
python test_ml_recipe_scoring.py
```

Expected output:
- ✅ ML predictions used when nutrition data available
- ✅ Confidence scores tracked (20-100%)
- ✅ Fallback to heuristics when needed
- ✅ Full pipeline integration working

---

## Benefits

| Before (Heuristics) | After (ML) |
|---------------------|------------|
| Simple calorie/protein rules | 98.99% accuracy |
| Fixed thresholds | Learned patterns |
| No confidence scores | Confidence tracking |
| 15% weight in scoring | 25% weight in scoring |
| Basic explanations | Rich debug info |

**Result**: Significantly more accurate recipe recommendations! 🎉
