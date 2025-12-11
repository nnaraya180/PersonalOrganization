"""
Example: How to integrate ML predictions into existing recipe scoring.

This shows how to use the new predict_both() function in your chat.py scoring logic.
"""
from ml.mood_energy_model import predict_both

def example_integration_in_scoring():
    """
    Example of how to use ML predictions in your existing score_recipes function.
    """
    
    # Assume you have a recipe object with nutrition data
    recipe = {
        'title': 'Chicken Stir Fry',
        'nutrition_calories': 450,
        'nutrition_protein_g': 28,
        'nutrition_carbs_g': 45,
        'nutrition_fat_g': 15,
        'nutrition_sugar_g': 8,
    }
    
    # Extract nutrition for prediction
    nutrition_data = {
        'calories': recipe.get('nutrition_calories'),
        'protein_g': recipe.get('nutrition_protein_g'),
        'carbs_g': recipe.get('nutrition_carbs_g'),
        'fat_g': recipe.get('nutrition_fat_g'),
        'sugar_g': recipe.get('nutrition_sugar_g'),
    }
    
    # Get ML predictions
    mood_result, energy_result = predict_both(nutrition_data)
    
    if mood_result and energy_result:
        print(f"\nRecipe: {recipe['title']}")
        print(f"Predicted Mood: {mood_result['label']} (confidence: {mood_result['confidence']:.0%})")
        print(f"Predicted Energy: {energy_result['label']} (confidence: {energy_result['confidence']:.0%})")
        print(f"Data Quality: {mood_result['data_quality']}")
        
        # Use in scoring
        mood_score = mood_result['score']  # 0-1 range
        energy_score = energy_result['score']  # 0-1 range
        
        # Example: Adjust based on user's current state
        user_mood = "stressed"  # from user constraints
        user_energy = "low"     # from user constraints
        
        # If user is stressed and recipe predicts positive mood:
        if user_mood in ["stressed", "anxious", "low"] and mood_result['label_index'] > 1:
            mood_score *= 1.2  # Boost score for mood-improving recipes
            
        # If user has low energy and recipe predicts high energy:
        if user_energy == "low" and energy_result['label'] == "Energy Burst":
            energy_score *= 1.3  # Boost score for energizing recipes
        
        print(f"\nAdjusted Scores:")
        print(f"  Mood Score: {mood_score:.2f}")
        print(f"  Energy Score: {energy_score:.2f}")
        
        return mood_score, energy_score
    else:
        print("Unable to make prediction (insufficient data)")
        return 0.5, 0.5  # neutral default


def example_batch_scoring():
    """
    Example of scoring multiple recipes efficiently.
    """
    recipes = [
        {
            'title': 'Chicken Salad',
            'nutrition_calories': 350,
            'nutrition_protein_g': 28,
            'nutrition_carbs_g': 12,
            'nutrition_fat_g': 22,
        },
        {
            'title': 'Pasta Carbonara',
            'nutrition_calories': 650,
            'nutrition_protein_g': 20,
            'nutrition_carbs_g': 75,
            'nutrition_fat_g': 28,
        },
        {
            'title': 'Fruit Smoothie',
            'nutrition_calories': 250,
            'nutrition_protein_g': 8,
            'nutrition_carbs_g': 45,
            'nutrition_fat_g': 3,
        }
    ]
    
    print("\n" + "="*60)
    print("BATCH SCORING EXAMPLE")
    print("="*60)
    
    for recipe in recipes:
        nutrition = {
            'calories': recipe.get('nutrition_calories'),
            'protein_g': recipe.get('nutrition_protein_g'),
            'carbs_g': recipe.get('nutrition_carbs_g'),
            'fat_g': recipe.get('nutrition_fat_g'),
        }
        
        mood_result, energy_result = predict_both(nutrition)
        
        print(f"\n{recipe['title']}:")
        print(f"  Mood: {mood_result['label']:12s} (score: {mood_result['score']:.2f})")
        print(f"  Energy: {energy_result['label']:12s} (score: {energy_result['score']:.2f})")


def example_with_user_preferences():
    """
    Example of using predictions with user preferences/constraints.
    """
    print("\n" + "="*60)
    print("USER PREFERENCE MATCHING")
    print("="*60)
    
    # User wants comfort food (mood) and sustained energy
    user_prefs = {
        'desired_mood': 'comfort',
        'desired_energy': 'sustained',
        'current_mood': 'stressed',
        'current_energy': 'low'
    }
    
    recipe = {
        'title': 'Mac and Cheese',
        'nutrition_calories': 550,
        'nutrition_protein_g': 22,
        'nutrition_carbs_g': 60,
        'nutrition_fat_g': 25,
    }
    
    nutrition = {
        'calories': recipe.get('nutrition_calories'),
        'protein_g': recipe.get('nutrition_protein_g'),
        'carbs_g': recipe.get('nutrition_carbs_g'),
        'fat_g': recipe.get('nutrition_fat_g'),
    }
    
    mood_result, energy_result = predict_both(nutrition)
    
    print(f"\nRecipe: {recipe['title']}")
    print(f"User wants: {user_prefs['desired_mood']}, {user_prefs['desired_energy']} energy")
    print(f"User current state: {user_prefs['current_mood']}, {user_prefs['current_energy']} energy")
    print(f"\nPredicted Effects:")
    print(f"  Mood: {mood_result['label']} (score: {mood_result['score']:.2f})")
    print(f"  Energy: {energy_result['label']} (score: {energy_result['score']:.2f})")
    
    # Calculate match score
    # High fat + high carbs often = comfort food
    comfort_score = (nutrition['fat_g'] / 30 + nutrition['carbs_g'] / 100) / 2
    
    # Protein + moderate carbs = sustained energy
    sustained_energy_score = (nutrition['protein_g'] / 30 + 
                              max(0, 1 - abs(nutrition['carbs_g'] - 50) / 50))
    
    print(f"\nMatch Scores:")
    print(f"  Comfort: {comfort_score:.2f}")
    print(f"  Sustained Energy: {sustained_energy_score:.2f}")
    
    # Final recommendation
    overall_score = (mood_result['score'] + energy_result['score'] + 
                    comfort_score + sustained_energy_score) / 4
    print(f"  Overall: {overall_score:.2f}")


if __name__ == "__main__":
    print("="*60)
    print("ML PREDICTION INTEGRATION EXAMPLES")
    print("="*60)
    
    # Example 1: Basic integration
    example_integration_in_scoring()
    
    # Example 2: Batch scoring
    example_batch_scoring()
    
    # Example 3: User preference matching
    example_with_user_preferences()
    
    print("\n" + "="*60)
    print("To integrate into your chat.py:")
    print("="*60)
    print("""
1. Import the prediction function:
   from ml.mood_energy_model import predict_both

2. In your compute_mood_score() function:
   mood_result, _ = predict_both(nutrition_dict)
   if mood_result:
       base_score = mood_result['score']
       # Adjust based on user constraints...
   
3. In your compute_energy_score() function:
   _, energy_result = predict_both(nutrition_dict)
   if energy_result:
       base_score = energy_result['score']
       # Adjust based on user constraints...

4. Add to debug info:
   debug['predicted_mood_effect'] = mood_result
   debug['predicted_energy_effect'] = energy_result
   debug['ml_confidence'] = mood_result['confidence']
    """)
