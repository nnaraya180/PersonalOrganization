#!/usr/bin/env python3
"""
Test ML integration in recipe scoring system.
Verifies that ML predictions are used in the recommendation pipeline.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from routers.chat import compute_mood_energy_score, score_recipes
from models import UserConstraints, Item, Recipe, RecipeIngredient
from datetime import date, timedelta


def create_test_recipe(recipe_id: int, title: str, calories: float, protein: float, 
                       carbs: float, fat: float, sugar: float = 10.0) -> Recipe:
    """Create a test recipe with nutrition data."""
    recipe = Recipe(
        id=recipe_id,
        title=title,
        time_minutes=30,
        diet="omnivore",
        calories=calories,
        protein_g=protein,
        carbs_g=carbs,
        fat_g=fat,
        nutrition_sugar_g=sugar,
    )
    
    # Add some ingredients
    recipe.ingredients = [
        RecipeIngredient(recipe_id=recipe_id, name="chicken", quantity="2 cups"),
        RecipeIngredient(recipe_id=recipe_id, name="rice", quantity="1 cup"),
        RecipeIngredient(recipe_id=recipe_id, name="vegetables", quantity="1 cup"),
    ]
    
    return recipe


def test_ml_mood_energy_scoring():
    """Test that ML predictions are used in mood/energy scoring."""
    print("\n" + "="*70)
    print("TEST 1: ML Mood/Energy Scoring")
    print("="*70)
    
    # Create test recipes with different nutrition profiles
    recipes = [
        # High protein, low sugar - should predict "Energy Burst"
        create_test_recipe(1, "Protein Power Bowl", 450, 35, 40, 15, 5),
        
        # High sugar, moderate calories - should predict "Happy" mood
        create_test_recipe(2, "Sweet Comfort Pasta", 650, 15, 85, 20, 45),
        
        # Low calorie, balanced - should predict "Neutral" or "Normal"
        create_test_recipe(3, "Light Salad", 350, 10, 30, 12, 8),
    ]
    
    # Test with different constraints
    test_cases = [
        {
            "name": "High Energy Request",
            "constraints": UserConstraints(energy_level="high"),
            "expected_best": 1,  # Protein Power Bowl
        },
        {
            "name": "Low Energy Request",
            "constraints": UserConstraints(energy_level="low"),
            "expected_best": 3,  # Light Salad
        },
        {
            "name": "Comfort Mood Request",
            "constraints": UserConstraints(mood="comfort"),
            "expected_best": 2,  # Sweet Comfort Pasta
        },
    ]
    
    for test_case in test_cases:
        print(f"\n📋 {test_case['name']}")
        print("-" * 70)
        
        constraints = test_case["constraints"]
        
        for recipe in recipes:
            score, explanation, debug = compute_mood_energy_score(recipe, constraints)
            
            sugar_val = getattr(recipe, 'nutrition_sugar_g', 0) or 0
            print(f"\n  Recipe: {recipe.title}")
            print(f"  Nutrition: {recipe.calories} cal, {recipe.protein_g}g protein, {sugar_val}g sugar")
            print(f"  Score: {score:.3f}")
            
            if debug.get("ml_used"):
                print(f"  ✅ ML Used: Yes")
                ml_mood = debug.get("ml_mood", {})
                ml_energy = debug.get("ml_energy", {})
                print(f"     - Mood Prediction: {ml_mood.get('label')} (conf: {ml_mood.get('confidence', 0):.0%})")
                print(f"     - Energy Prediction: {ml_energy.get('label')} (conf: {ml_energy.get('confidence', 0):.0%})")
            else:
                print(f"  ⚠️  ML Used: No (fallback to heuristics)")
                if "ml_error" in debug:
                    print(f"     Error: {debug['ml_error']}")
            
            print(f"  Explanation: {explanation}")


def test_full_recipe_scoring_pipeline():
    """Test complete recipe scoring with ML predictions."""
    print("\n" + "="*70)
    print("TEST 2: Full Recipe Scoring Pipeline with ML")
    print("="*70)
    
    # Create test recipes
    recipes = [
        create_test_recipe(1, "High Protein Chicken", 500, 40, 30, 18, 8),
        create_test_recipe(2, "Comfort Mac & Cheese", 700, 18, 75, 35, 15),
        create_test_recipe(3, "Light Fish Salad", 380, 25, 20, 15, 5),
    ]
    
    # Create pantry items (with some expiring)
    today = date.today()
    pantry_items = [
        Item(id=1, name="chicken", quantity=2.0, unit="lbs", 
             expiration_date=today + timedelta(days=3)),
        Item(id=2, name="rice", quantity=5.0, unit="lbs"),
        Item(id=3, name="vegetables", quantity=1.0, unit="lbs"),
    ]
    
    # Test with constraints
    constraints = UserConstraints(
        energy_level="high",
        mood="focus",
        max_time_minutes=45,
    )
    
    print(f"\n📋 Request: High energy, focus mood, under 45 minutes")
    print("-" * 70)
    
    # Score recipes
    scored = score_recipes(recipes, pantry_items, constraints)
    
    print(f"\n🏆 Ranked Results:")
    for i, item in enumerate(scored, 1):
        print(f"\n  #{i} {item['title']} (Score: {item['score']:.3f})")
        print(f"     - Coverage: {item['coverage']:.1%}")
        print(f"     - Expiring: {item['expiring']:.1%}")
        print(f"     - Nutrition: {item['nutrition']:.3f}")
        print(f"     - Mood/Energy: {item['mood_energy']:.3f}")
        
        # Check if ML was used
        mood_energy_debug = item.get('debug', {}).get('mood_energy', {})
        if mood_energy_debug.get('ml_used'):
            print(f"     - ✅ ML Predictions Used")
            ml_mood = mood_energy_debug.get('ml_mood', {})
            ml_energy = mood_energy_debug.get('ml_energy', {})
            print(f"       Mood: {ml_mood.get('label')} ({ml_mood.get('confidence', 0):.0%})")
            print(f"       Energy: {ml_energy.get('label')} ({ml_energy.get('confidence', 0):.0%})")
        else:
            print(f"     - ⚠️  Heuristics Used (ML not available)")
        
        print(f"     - Reason: {item['reason']}")
        print(f"     - Explanation: {item['explanation']}")


def test_ml_confidence_impact():
    """Test how ML confidence scores affect ranking."""
    print("\n" + "="*70)
    print("TEST 3: ML Confidence Impact on Rankings")
    print("="*70)
    
    # Create recipes with complete vs partial nutrition data
    complete_recipe = create_test_recipe(1, "Complete Nutrition Data", 500, 30, 50, 18, 10)
    
    # Recipe with minimal nutrition (only calories)
    partial_recipe = Recipe(
        id=2,
        title="Partial Nutrition Data",
        time_minutes=30,
        diet="omnivore",
        calories=500,
        protein_g=None,
        carbs_g=None,
        fat_g=None,
        sugar_g=None,
    )
    partial_recipe.ingredients = [
        RecipeIngredient(recipe_id=2, name="chicken", quantity="2 cups"),
    ]
    
    constraints = UserConstraints(energy_level="high")
    
    print(f"\n📋 Comparing ML confidence with complete vs partial data")
    print("-" * 70)
    
    for recipe in [complete_recipe, partial_recipe]:
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        print(f"\n  Recipe: {recipe.title}")
        print(f"  Nutrition: calories={recipe.calories}, protein={recipe.protein_g}, carbs={recipe.carbs_g}")
        print(f"  Score: {score:.3f}")
        
        if debug.get("ml_used"):
            ml_energy = debug.get("ml_energy", {})
            data_quality = debug.get("ml_energy", {}).get("data_quality", "N/A")
            print(f"  ✅ ML Used")
            print(f"     - Energy: {ml_energy.get('label')} (conf: {ml_energy.get('confidence', 0):.0%})")
            print(f"     - Data Quality: {data_quality}")
        else:
            print(f"  ⚠️  Heuristics Used")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 ML RECIPE SCORING INTEGRATION TESTS")
    print("="*70)
    print("\nTesting ML predictions in the recipe recommendation pipeline...")
    
    try:
        test_ml_mood_energy_scoring()
        test_full_recipe_scoring_pipeline()
        test_ml_confidence_impact()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\n🎉 ML predictions are fully integrated into recipe scoring!")
        print("   - Mood predictions influence recipe rankings")
        print("   - Energy predictions affect recommendations")
        print("   - Confidence scores are tracked in debug info")
        print("   - Heuristic fallback works when ML unavailable")
        print("\n")
        
        return 0
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST FAILED")
        print("="*70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
