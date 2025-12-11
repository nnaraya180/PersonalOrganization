"""
Quick test to verify ML models are working before starting the server.
"""
import sys
sys.path.insert(0, '/Users/neilnarayanan/code/personal-assistant/backend')

from ml.mood_energy_model import predict_both
from ml.nutrition_import import parse_recipe_nutrition

print("="*60)
print("TESTING ML MODEL INTEGRATION")
print("="*60)

# Test 1: Direct prediction with complete data
print("\n1. Testing prediction with complete data:")
complete_data = {
    'calories': 450,
    'protein_g': 25,
    'carbs_g': 50,
    'fat_g': 15,
    'sugar_g': 8
}

mood, energy = predict_both(complete_data)
if mood and energy:
    print(f"   ✓ Mood: {mood['label']} (confidence: {mood['confidence']:.2%})")
    print(f"   ✓ Energy: {energy['label']} (confidence: {energy['confidence']:.2%})")
else:
    print("   ✗ Prediction failed")
    sys.exit(1)

# Test 2: Partial data (only calories)
print("\n2. Testing prediction with partial data (calories only):")
partial_data = {'calories': 450}

mood, energy = predict_both(partial_data)
if mood and energy:
    print(f"   ✓ Mood: {mood['label']} (confidence: {mood['confidence']:.2%})")
    print(f"   ✓ Estimated: {mood['estimated_fields']}")
    print(f"   ✓ Data quality: {mood['data_quality']}")
else:
    print("   ✗ Prediction failed")
    sys.exit(1)

# Test 3: Nutrition import
print("\n3. Testing nutrition import:")
recipe_data = {
    'name': 'Chicken Salad',
    'calories': 350,
    'protein': 28,
    'carbs': 12,
    'fat': 22
}

nutrition_obj = parse_recipe_nutrition('generic', recipe_data)
print(f"   ✓ Completeness: {nutrition_obj.get_completeness():.1%}")
print(f"   ✓ Missing: {nutrition_obj.get_missing_fields()}")

mood, energy = predict_both(nutrition_obj.to_dict())
if mood and energy:
    print(f"   ✓ Mood: {mood['label']}")
    print(f"   ✓ Energy: {energy['label']}")
else:
    print("   ✗ Prediction failed")
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL TESTS PASSED - ML models are ready!")
print("="*60)
print("\nYou can now start the FastAPI server with:")
print("  cd backend && uvicorn main:app --reload")
print("\nNew endpoints available at:")
print("  POST /api/ml/predict-mood-energy")
print("  POST /api/ml/import-recipe")
print("  GET  /api/ml/health")
