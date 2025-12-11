# 🚀 Quick Reference Card

## Start Server
```bash
cd backend
uvicorn main:app --reload
```

## Test Endpoints

### Health Check
```bash
curl http://localhost:8000/api/ml/health
```

### Predict (Complete Data)
```bash
curl -X POST http://localhost:8000/api/ml/predict-mood-energy \
  -H "Content-Type: application/json" \
  -d '{
    "nutrition": {
      "calories": 450,
      "protein_g": 25,
      "carbs_g": 50,
      "fat_g": 15
    }
  }'
```

### Predict (Partial Data)
```bash
curl -X POST http://localhost:8000/api/ml/predict-mood-energy \
  -H "Content-Type: application/json" \
  -d '{"nutrition": {"calories": 450}}'
```

### Import Recipe
```bash
curl -X POST http://localhost:8000/api/ml/import-recipe \
  -H "Content-Type: application/json" \
  -d '{
    "source": "generic",
    "recipe_data": {
      "name": "Chicken Salad",
      "calories": 350,
      "protein": 28,
      "carbs": 12,
      "fat": 22
    }
  }'
```

## Use in Python

```python
from ml.mood_energy_model import predict_both

# Predict
mood, energy = predict_both({
    'calories': 450,
    'protein_g': 25,
    'carbs_g': 50,
    'fat_g': 15
})

# Access results
print(mood['label'])           # "Neutral", "Happy", or "Sad"
print(mood['score'])           # 0-1 range
print(mood['confidence'])      # 0-1 range
print(mood['data_quality'])    # "high", "medium", or "low"
print(mood['estimated_fields']) # List of fields that were estimated
```

## Model Accuracy
- **Mood**: 98.99%
- **Energy**: 88.75%

## Key Features
✅ Handles incomplete nutrition data  
✅ Confidence scores included  
✅ Multi-format API support  
✅ Feature engineering included  
✅ Intelligent missing data estimation  

## Files to Know
- `ML_INTEGRATION_GUIDE.md` - Full documentation
- `ARCHITECTURE.md` - System design
- `example_ml_integration.py` - Usage examples
- `test_ml_endpoints.py` - Integration tests

## Retrain Models
```bash
cd analysis
python train_mood_energy_model.py
```

## Response Fields

### Mood/Energy Prediction
```json
{
  "label": "Happy|Neutral|Sad / Energy Burst|Low|Normal",
  "label_index": 0-2,
  "score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "estimated_fields": ["field1", "field2"],
  "data_quality": "high|medium|low"
}
```

### Import Recipe
```json
{
  "nutrition": {...},
  "completeness": 0.0-1.0,
  "missing_fields": [...],
  "predictions": {
    "mood": {...},
    "energy": {...}
  }
}
```

## Supported Data Formats

### Generic JSON
```json
{
  "calories": 350,
  "protein": 25,
  "carbs": 45,
  "fat": 12,
  "sugar": 8,
  "fiber": 3
}
```

### Spoonacular
```python
parse_recipe_nutrition('spoonacular', response)
```

### Edamam
```python
parse_recipe_nutrition('edamam', response)
```

### USDA
```python
parse_recipe_nutrition('usda', response)
```

## Feature Names
- Calories
- Total Fat (g)
- Total Sugars (g)
- Carbohydrates (Carbs) (g)
- Protein (g)
- protein_to_carb_ratio
- fat_to_carb_ratio
- protein_pct
- carb_pct
- fat_pct
- sugar_to_total_carb
- sugar_load
- caloric_density
- protein_score

## Common Use Cases

### Case 1: Simple Prediction
```python
mood, energy = predict_both({'calories': 450})
```

### Case 2: Full Nutrition Data
```python
mood, energy = predict_both({
    'calories': 450,
    'protein_g': 25,
    'carbs_g': 50,
    'fat_g': 15,
    'sugar_g': 8
})
```

### Case 3: Import from API
```python
from ml.nutrition_import import parse_recipe_nutrition
nutrition = parse_recipe_nutrition('spoonacular', api_response)
mood, energy = predict_both(nutrition.to_dict())
```

### Case 4: Batch Scoring
```python
recipes = [...]
scores = []
for recipe in recipes:
    mood, energy = predict_both(recipe.nutrition)
    scores.append((recipe.id, mood['score'], energy['score']))
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Models not found | Run `python verify_ml_integration.py` |
| No response | Check server is running at port 8000 |
| Low confidence | Provide more nutrition fields (not just calories) |
| Import fails | Check `source` parameter matches API type |
| Module not found | Install with `pip install scikit-learn joblib requests` |

## Next Steps
1. Integrate into `routers/chat.py`
2. Update recipe scoring functions
3. Add to debug info
4. Test with real recipes
5. Collect user feedback for model improvement

---

**You have everything you need!** 🎉
