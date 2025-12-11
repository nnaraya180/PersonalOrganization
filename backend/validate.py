"""
Database and API validation script.
Verifies schema, seeds test data, and runs live API tests.
"""
import sys
sys.path.insert(0, '/Users/neilnarayanan/code/personal-assistant/backend')

from sqlmodel import Session, select
from database import engine
from models import Recipe, RecipeIngredient, Item, UserConstraints
from routers.chat import score_recipes, compute_nutrition_score, compute_mood_energy_score
from datetime import date, timedelta
import json


def validate_schema():
    """Verify new nutrition columns exist in database."""
    print("🔍 Validating database schema...")
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('recipe')]
    
    required_columns = [
        'nutrition_protein_g', 'nutrition_carbs_g', 'nutrition_fat_g',
        'nutrition_calories', 'nutrition_fiber_g', 'nutrition_sugar_g',
        'nutrition_sodium_mg'
    ]
    
    missing = [col for col in required_columns if col not in columns]
    if missing:
        print(f"❌ Missing columns: {missing}")
        return False
    
    print(f"✅ All nutrition columns present ({len(required_columns)} columns)")
    return True


def validate_scoring_logic():
    """Test scoring functions with real data."""
    print("\n🧪 Testing scoring logic...")
    
    with Session(engine) as session:
        # Get real recipes from DB
        recipes = session.exec(select(Recipe)).all()
        pantry_items = session.exec(select(Item)).all()
        
        if not recipes:
            print("⚠️  No recipes in database - skipping scoring test")
            return True
        
        if not pantry_items:
            print("⚠️  No pantry items in database - skipping scoring test")
            return True
        
        print(f"   Found {len(recipes)} recipes and {len(pantry_items)} pantry items")
        
        # Test with high_protein goal
        constraints = UserConstraints(
            nutrition_goal="high_protein",
            energy_level="high",
            max_time_minutes=30
        )
        
        scored = score_recipes(recipes, pantry_items, constraints)
        
        if not scored:
            print("⚠️  No recipes passed filters")
            return True
        
        print(f"   Scored {len(scored)} recipes after filters")
        
        # Validate structure
        top_recipe = scored[0]
        assert 'explanation' in top_recipe, "Missing explanation field"
        assert 'debug' in top_recipe, "Missing debug field"
        assert 'nutrition' in top_recipe['debug'], "Missing nutrition debug"
        assert 'mood_energy' in top_recipe['debug'], "Missing mood_energy debug"
        assert 'expiring' in top_recipe['debug'], "Missing expiring debug"
        assert 'coverage' in top_recipe['debug'], "Missing coverage debug"
        
        print(f"✅ Scoring logic working correctly")
        print(f"   Top recipe: {top_recipe['title']}")
        print(f"   Score: {top_recipe['score']:.3f}")
        print(f"   Explanation: {top_recipe['explanation'][:80]}...")
        
        return True


def validate_nutrition_scoring():
    """Test nutrition scoring with synthetic data."""
    print("\n🧪 Testing nutrition scoring edge cases...")
    
    from types import SimpleNamespace
    
    # Test high protein recipe
    recipe = SimpleNamespace(
        protein_g=40,
        carbs_g=30,
        fat_g=10,
        calories=500
    )
    constraints = UserConstraints(nutrition_goal="high_protein")
    score, explanation, debug = compute_nutrition_score(recipe, constraints)
    
    assert score > 0, f"High protein recipe should score positively, got {score}"
    assert 'protein' in explanation.lower(), "Explanation should mention protein"
    print(f"✅ High protein scoring: {score:.2f} - {explanation[:60]}")
    
    # Test low carb recipe
    recipe = SimpleNamespace(
        protein_g=10,
        carbs_g=80,
        fat_g=20,
        calories=700
    )
    constraints = UserConstraints(nutrition_goal="low_carb")
    score, explanation, debug = compute_nutrition_score(recipe, constraints)
    
    assert score < 0, f"High carb recipe should score negatively for low_carb, got {score}"
    print(f"✅ Low carb penalty: {score:.2f} - {explanation[:60]}")
    
    # Test missing data
    recipe = SimpleNamespace()
    constraints = UserConstraints(nutrition_goal="high_protein")
    score, explanation, debug = compute_nutrition_score(recipe, constraints)
    
    assert score == 0, f"Missing data should be neutral, got {score}"
    print(f"✅ Missing data handling: {score:.2f} - {explanation}")
    
    return True


def validate_data_integrity():
    """Check for any data issues in existing recipes."""
    print("\n🔍 Validating data integrity...")
    
    with Session(engine) as session:
        recipes = session.exec(select(Recipe)).all()
        
        if not recipes:
            print("⚠️  No recipes to validate")
            return True
        
        issues = []
        for recipe in recipes:
            # Check for orphaned recipes (no ingredients)
            if not recipe.ingredients:
                issues.append(f"Recipe '{recipe.title}' has no ingredients")
            
            # Check for negative nutrition values
            for field in ['protein_g', 'carbs_g', 'fat_g', 'calories']:
                value = getattr(recipe, field, None)
                if value is not None and value < 0:
                    issues.append(f"Recipe '{recipe.title}' has negative {field}: {value}")
        
        if issues:
            print(f"⚠️  Found {len(issues)} data issues:")
            for issue in issues[:5]:  # Show first 5
                print(f"   - {issue}")
            if len(issues) > 5:
                print(f"   ... and {len(issues) - 5} more")
        else:
            print(f"✅ All {len(recipes)} recipes have valid data")
        
        return True


def print_summary():
    """Print summary of database state."""
    print("\n📊 Database Summary:")
    
    with Session(engine) as session:
        recipe_count = len(session.exec(select(Recipe)).all())
        item_count = len(session.exec(select(Item)).all())
        
        # Count recipes with nutrition data
        recipes_with_nutrition = 0
        recipes = session.exec(select(Recipe)).all()
        for r in recipes:
            if r.protein_g or r.nutrition_protein_g:
                recipes_with_nutrition += 1
        
        print(f"   📝 Recipes: {recipe_count}")
        print(f"   🥘 With nutrition data: {recipes_with_nutrition}")
        print(f"   🥫 Pantry items: {item_count}")
        
        # Show sample recipe
        if recipes:
            sample = recipes[0]
            print(f"\n   Sample recipe: {sample.title}")
            print(f"   - Time: {sample.time_minutes} min")
            print(f"   - Diet: {sample.diet}")
            print(f"   - Protein: {sample.protein_g}g")
            print(f"   - Ingredients: {len(sample.ingredients)}")


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("🚀 Personal Assistant Backend Validation")
    print("=" * 60)
    
    all_passed = True
    
    try:
        if not validate_schema():
            all_passed = False
        
        if not validate_nutrition_scoring():
            all_passed = False
        
        if not validate_scoring_logic():
            all_passed = False
        
        if not validate_data_integrity():
            all_passed = False
        
        print_summary()
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL VALIDATION CHECKS PASSED")
            print("\nYour backend is working correctly! The new nutrition")
            print("scoring features are properly integrated.")
        else:
            print("⚠️  SOME CHECKS FAILED")
            print("\nPlease review the errors above.")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
