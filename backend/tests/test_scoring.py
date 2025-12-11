"""
Unit tests for scoring functions in routers/chat.py
Tests nutrition scoring, mood/energy scoring, expiring items, and edge cases.
"""
import pytest
from types import SimpleNamespace
from datetime import date, timedelta
import sys
sys.path.insert(0, '/Users/neilnarayanan/code/personal-assistant/backend')

from routers.chat import (
    compute_nutrition_score,
    compute_mood_energy_score,
    compute_expiring_score,
    infer_nutrition_goal,
    _get_macro,
    score_recipes,
)
from models import UserConstraints, Item


def make_recipe(**kwargs):
    """Helper to create recipe-like object with attributes."""
    return SimpleNamespace(**kwargs)


def make_item(**kwargs):
    """Helper to create Item-like object."""
    defaults = {
        'id': 1,
        'name': 'test',
        'category': 'pantry',
        'quantity': 1,
        'purchase_date': None,
        'expiration_date': None,
        'estimated_calories': None,
        'estimated_protein_g': None,
        'estimated_carbs_g': None,
        'estimated_fat_g': None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestNutritionScoring:
    """Tests for compute_nutrition_score function."""
    
    def test_high_protein_goal_strong_match(self):
        """Recipe with 40g protein should score highly for high_protein goal."""
        recipe = make_recipe(protein_g=40, carbs_g=30, fat_g=10, calories=500)
        constraints = UserConstraints(nutrition_goal="high_protein")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score > 0.5, "High protein recipe should score positively"
        assert 'protein_g' in debug['macros']
        assert debug['macros']['protein_g'] == 40
        assert 'well above' in explanation or 'meets' in explanation
    
    def test_high_protein_goal_weak_match(self):
        """Recipe with 10g protein should score poorly for high_protein goal."""
        recipe = make_recipe(protein_g=10, carbs_g=60, fat_g=15, calories=600)
        constraints = UserConstraints(nutrition_goal="high_protein")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score < 0, "Low protein recipe should score negatively for high_protein goal"
        assert 'below' in explanation
    
    def test_low_carb_goal_good_match(self):
        """Recipe with 20g carbs should score well for low_carb goal."""
        recipe = make_recipe(protein_g=30, carbs_g=20, fat_g=15, calories=450)
        constraints = UserConstraints(prioritize_macro="low_carb")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score > 0, "Low carb recipe should score positively"
        assert 'under' in explanation
    
    def test_low_carb_goal_exceeds_limit(self):
        """Recipe with 80g carbs should score poorly for low_carb goal."""
        recipe = make_recipe(protein_g=10, carbs_g=80, fat_g=20, calories=700)
        constraints = UserConstraints(nutrition_goal="low_carb")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score < 0, "High carb recipe should score negatively for low_carb goal"
        assert 'exceeds' in explanation
    
    def test_low_calorie_goal_good_match(self):
        """Recipe with 400 calories should score well for low_calorie goal."""
        recipe = make_recipe(protein_g=20, carbs_g=40, fat_g=8, calories=400)
        constraints = UserConstraints(nutrition_goal="low_calorie")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score > 0, "Low calorie recipe should score positively"
    
    def test_no_nutrition_goal(self):
        """Recipe with no goal specified should return neutral score."""
        recipe = make_recipe(protein_g=25, carbs_g=40, fat_g=12, calories=500)
        constraints = UserConstraints()
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score == 0.0, "No goal should result in neutral score"
        assert 'No nutrition goal' in explanation
    
    def test_missing_macro_data(self):
        """Recipe missing nutrition data should handle gracefully."""
        recipe = make_recipe()  # No nutrition fields
        constraints = UserConstraints(nutrition_goal="high_protein")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score == 0.0, "Missing data should result in neutral score"
        assert 'No nutrition data' in explanation
        assert 'protein_g' in debug['missing_macros']
    
    def test_energy_level_infers_goal(self):
        """High energy level should infer high_protein goal."""
        recipe = make_recipe(protein_g=35, carbs_g=40, fat_g=10, calories=550)
        constraints = UserConstraints(energy_level="high")
        
        score, explanation, debug = compute_nutrition_score(recipe, constraints)
        
        assert score > 0, "High energy should benefit from high protein"
        assert debug['goal'] == 'high_protein'


class TestMoodEnergyScoring:
    """Tests for compute_mood_energy_score function."""
    
    def test_low_energy_prefers_light_quick(self):
        """Low energy should prefer lighter, quicker meals."""
        recipe = make_recipe(calories=450, fat_g=8, protein_g=10, time_minutes=15)
        constraints = UserConstraints(energy_level="low")
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score > 0, "Light and quick should score well for low energy"
        assert 'lighter' in explanation or 'quick' in explanation
    
    def test_high_energy_prefers_protein(self):
        """High energy should prefer higher protein meals."""
        recipe = make_recipe(calories=650, fat_g=15, protein_g=35, time_minutes=25)
        constraints = UserConstraints(energy_level="high")
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score > 0, "High protein should score well for high energy"
        assert 'protein' in explanation
    
    def test_comfort_mood_prefers_hearty(self):
        """Comfort mood should prefer heartier meals."""
        recipe = make_recipe(calories=750, fat_g=25, protein_g=20, time_minutes=30)
        constraints = UserConstraints(mood="comfort")
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score > 0, "Hearty meals should score well for comfort mood"
        assert 'comfort' in explanation
    
    def test_light_mood_prefers_light_meals(self):
        """Light mood should prefer lighter meals."""
        recipe = make_recipe(calories=400, fat_g=8, protein_g=18, time_minutes=20)
        constraints = UserConstraints(mood="light")
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score > 0, "Light meals should score well for light mood"
        assert 'light' in explanation
    
    def test_focus_mood_needs_protein(self):
        """Focus mood should benefit from protein."""
        recipe = make_recipe(calories=550, fat_g=12, protein_g=30, time_minutes=25)
        constraints = UserConstraints(mood="focus")
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score > 0, "Protein should score well for focus mood"
    
    def test_no_mood_or_energy_neutral(self):
        """No mood/energy specified should be neutral."""
        recipe = make_recipe(calories=500, fat_g=15, protein_g=20, time_minutes=25)
        constraints = UserConstraints()
        
        score, explanation, debug = compute_mood_energy_score(recipe, constraints)
        
        assert score == 0.0, "No mood/energy should be neutral"


class TestExpiringScoring:
    """Tests for compute_expiring_score function."""
    
    def test_expiring_items_matched(self):
        """Recipe using expiring ingredients should score highly."""
        today = date.today()
        recipe = SimpleNamespace(
            ingredients=[
                SimpleNamespace(name='milk'),
                SimpleNamespace(name='eggs'),
                SimpleNamespace(name='butter'),
            ]
        )
        pantry_items = [
            make_item(name='milk', expiration_date=(today + timedelta(days=2))),
            make_item(name='eggs', expiration_date=(today + timedelta(days=3))),
            make_item(name='flour', expiration_date=(today + timedelta(days=30))),
        ]
        
        score, matched = compute_expiring_score(recipe, pantry_items)
        
        assert score > 0, "Should score positively for expiring items"
        assert 'milk' in matched
        assert 'eggs' in matched
        assert len(matched) == 2
    
    def test_soon_expiring_lower_weight(self):
        """Items expiring in 7-14 days should have lower weight."""
        today = date.today()
        recipe = SimpleNamespace(
            ingredients=[SimpleNamespace(name='cheese')]
        )
        pantry_items = [
            make_item(name='cheese', expiration_date=(today + timedelta(days=10))),
        ]
        
        score, matched = compute_expiring_score(recipe, pantry_items)
        
        assert 0 < score <= 0.5, "Soon expiring should have moderate score"
        assert 'cheese' in matched
    
    def test_no_expiring_items(self):
        """Recipe with no expiring ingredients should score zero."""
        today = date.today()
        recipe = SimpleNamespace(
            ingredients=[SimpleNamespace(name='rice')]
        )
        pantry_items = [
            make_item(name='rice', expiration_date=(today + timedelta(days=365))),
        ]
        
        score, matched = compute_expiring_score(recipe, pantry_items)
        
        assert score == 0.0, "No expiring items should score zero"
        assert len(matched) == 0
    
    def test_empty_recipe_ingredients(self):
        """Recipe with no ingredients should handle gracefully."""
        recipe = SimpleNamespace(ingredients=[])
        pantry_items = []
        
        score, matched = compute_expiring_score(recipe, pantry_items)
        
        assert score == 0.0
        assert matched == []
    
    def test_substring_matching(self):
        """Should match ingredients via substring (e.g., 'milk' in 'whole milk')."""
        today = date.today()
        recipe = SimpleNamespace(
            ingredients=[SimpleNamespace(name='whole milk')]
        )
        pantry_items = [
            make_item(name='milk', expiration_date=(today + timedelta(days=2))),
        ]
        
        score, matched = compute_expiring_score(recipe, pantry_items)
        
        assert score > 0
        assert 'milk' in matched


class TestInferNutritionGoal:
    """Tests for infer_nutrition_goal helper."""
    
    def test_explicit_goal_takes_priority(self):
        """Explicit nutrition_goal should override other hints."""
        constraints = UserConstraints(
            nutrition_goal="low_carb",
            energy_level="high",
            prioritize_macro="high_protein"
        )
        
        goal = infer_nutrition_goal(constraints)
        
        assert goal == "low_carb"
    
    def test_prioritize_macro_used(self):
        """prioritize_macro should be used if no explicit goal."""
        constraints = UserConstraints(prioritize_macro="high_protein")
        
        goal = infer_nutrition_goal(constraints)
        
        assert goal == "high_protein"
    
    def test_high_energy_infers_protein(self):
        """High energy should infer high_protein goal."""
        constraints = UserConstraints(energy_level="High")
        
        goal = infer_nutrition_goal(constraints)
        
        assert goal == "high_protein"
    
    def test_low_energy_infers_low_calorie(self):
        """Low energy should infer low_calorie goal."""
        constraints = UserConstraints(energy_level="Low")
        
        goal = infer_nutrition_goal(constraints)
        
        assert goal == "low_calorie"
    
    def test_no_hints_returns_none(self):
        """No hints should return None."""
        constraints = UserConstraints()
        
        goal = infer_nutrition_goal(constraints)
        
        assert goal is None


class TestGetMacro:
    """Tests for _get_macro helper."""
    
    def test_base_field_present(self):
        """Should return value from base field if present."""
        recipe = make_recipe(protein_g=25)
        
        value = _get_macro(recipe, "protein_g")
        
        assert value == 25
    
    def test_nutrition_field_fallback(self):
        """Should fallback to nutrition_* field if base missing."""
        recipe = make_recipe(nutrition_protein_g=30)
        
        value = _get_macro(recipe, "protein_g")
        
        assert value == 30
    
    def test_both_fields_base_wins(self):
        """Base field should take priority over nutrition_* field."""
        recipe = make_recipe(protein_g=25, nutrition_protein_g=30)
        
        value = _get_macro(recipe, "protein_g")
        
        assert value == 25
    
    def test_missing_returns_none(self):
        """Missing fields should return None."""
        recipe = make_recipe()
        
        value = _get_macro(recipe, "protein_g")
        
        assert value is None


class TestScoreRecipesIntegration:
    """Integration tests for score_recipes function."""
    
    def test_basic_scoring_and_sorting(self):
        """Should score and sort recipes correctly."""
        today = date.today()
        recipes = [
            SimpleNamespace(
                id=1,
                title="High Protein Bowl",
                time_minutes=20,
                diet="vegetarian",
                protein_g=35,
                carbs_g=40,
                fat_g=12,
                calories=500,
                ingredients=[
                    SimpleNamespace(name='chicken'),
                    SimpleNamespace(name='rice'),
                ]
            ),
            SimpleNamespace(
                id=2,
                title="Low Protein Snack",
                time_minutes=10,
                diet="vegan",
                protein_g=5,
                carbs_g=30,
                fat_g=8,
                calories=300,
                ingredients=[
                    SimpleNamespace(name='crackers'),
                ]
            ),
        ]
        pantry_items = [
            make_item(name='chicken', expiration_date=(today + timedelta(days=2))),
            make_item(name='rice'),
            make_item(name='crackers'),
        ]
        constraints = UserConstraints(nutrition_goal="high_protein")
        
        scored = score_recipes(recipes, pantry_items, constraints)
        
        assert len(scored) == 2
        assert scored[0]['recipe_id'] == 1, "High protein recipe should rank first"
        assert scored[0]['nutrition'] > 0
        assert 'explanation' in scored[0]
        assert 'debug' in scored[0]
    
    def test_hard_filter_time(self):
        """Recipes exceeding time limit should be filtered out."""
        recipes = [
            SimpleNamespace(
                id=1,
                title="Quick Meal",
                time_minutes=15,
                diet=None,
                protein_g=20,
                carbs_g=30,
                fat_g=10,
                calories=400,
                ingredients=[SimpleNamespace(name='pasta')]
            ),
            SimpleNamespace(
                id=2,
                title="Slow Cook",
                time_minutes=60,
                diet=None,
                protein_g=25,
                carbs_g=40,
                fat_g=15,
                calories=500,
                ingredients=[SimpleNamespace(name='beef')]
            ),
        ]
        pantry_items = [make_item(name='pasta'), make_item(name='beef')]
        constraints = UserConstraints(max_time_minutes=30)
        
        scored = score_recipes(recipes, pantry_items, constraints)
        
        assert len(scored) == 1
        assert scored[0]['recipe_id'] == 1
    
    def test_hard_filter_exclude_ingredients(self):
        """Recipes with excluded ingredients should be filtered out."""
        recipes = [
            SimpleNamespace(
                id=1,
                title="Dairy Free",
                time_minutes=20,
                diet="vegan",
                protein_g=15,
                carbs_g=40,
                fat_g=10,
                calories=400,
                ingredients=[SimpleNamespace(name='tofu'), SimpleNamespace(name='rice')]
            ),
            SimpleNamespace(
                id=2,
                title="With Cheese",
                time_minutes=20,
                diet="vegetarian",
                protein_g=20,
                carbs_g=30,
                fat_g=15,
                calories=450,
                ingredients=[SimpleNamespace(name='pasta'), SimpleNamespace(name='cheese')]
            ),
        ]
        pantry_items = [
            make_item(name='tofu'),
            make_item(name='rice'),
            make_item(name='pasta'),
            make_item(name='cheese'),
        ]
        constraints = UserConstraints(exclude_ingredients=['cheese', 'dairy'])
        
        scored = score_recipes(recipes, pantry_items, constraints)
        
        assert len(scored) == 1
        assert scored[0]['recipe_id'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
