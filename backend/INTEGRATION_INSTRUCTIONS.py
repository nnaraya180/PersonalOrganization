"""
INTEGRATION GUIDE: Adding ML Predictions to Existing chat.py

This file shows the exact code changes needed to integrate the new ML models
into your existing recipe scoring logic in backend/routers/chat.py.
"""

# ============================================================================
# STEP 1: Add imports at the top of chat.py
# ============================================================================

"""
Add this import near the top of backend/routers/chat.py:
"""

from ml.mood_energy_model import predict_both


# ============================================================================
# STEP 2: Update compute_mood_energy_score() to use ML predictions
# ============================================================================

"""
REPLACE the existing compute_mood_energy_score() function with this:
"""

def compute_mood_energy_score(recipe: Any, constraints: UserConstraints) -> tuple[float, str, dict]:
    """
    ML-based mood/energy alignment score using trained models.
    Returns score in [-1, 1], explanation, and debug info.
    """
    mood = (constraints.mood or "").lower()
    energy = (constraints.energy_level or "").lower()
    
    # Extract nutrition data
    nutrition_data = {
        'calories': _get_macro(recipe, "calories"),
        'protein_g': _get_macro(recipe, "protein_g"),
        'carbs_g': _get_macro(recipe, "carbs_g"),
        'fat_g': _get_macro(recipe, "fat_g"),
        'sugar_g': _get_macro(recipe, "sugar_g"),
    }
    
    # Get ML predictions
    mood_result, energy_result = predict_both(nutrition_data)
    
    # Initialize with neutral score
    score = 0.0
    reasons: List[str] = []
    
    if mood_result and energy_result:
        # Mood alignment
        mood_label = mood_result['label'].lower()
        mood_score = mood_result['score']  # 0-1 range
        
        # Energy alignment
        energy_label = energy_result['label'].lower()
        energy_score = energy_result['score']  # 0-1 range
        
        # Adjust based on user's current state
        
        # Mood matching
        if mood in ["low", "down", "stressed", "anxious"]:
            # User needs mood boost - prefer Happy predictions
            if mood_label == "happy":
                score += 0.5
                reasons.append("predicted to improve mood when you're feeling low")
            elif mood_label == "neutral":
                score += 0.2
                reasons.append("predicted to stabilize mood")
        elif mood in ["comfort", "cozy", "hearty"]:
            # User wants comfort - neutral/happy are good
            if mood_label in ["neutral", "happy"]:
                score += 0.4
                reasons.append("comforting meal predicted to match your mood")
        elif mood in ["light", "fresh", "healthy"]:
            # User wants light - prefer neutral
            if mood_label == "neutral":
                score += 0.3
                reasons.append("light meal as requested")
        
        # Energy matching
        if energy == "low":
            # User needs energy boost
            if energy_label == "energy burst":
                score += 0.5
                reasons.append("predicted to boost energy when you're feeling low")
            elif energy_label == "normal":
                score += 0.2
                reasons.append("predicted to provide steady energy")
        elif energy == "high":
            # User already energized - prefer normal/steady
            if energy_label == "normal":
                score += 0.3
                reasons.append("predicted to maintain your energy level")
        else:
            # Neutral energy state - any prediction is okay
            if energy_label == "energy burst":
                score += 0.2
                reasons.append("energizing meal option")
        
        # Confidence adjustment
        confidence = (mood_result['confidence'] + energy_result['confidence']) / 2
        if confidence < 0.5:
            score *= 0.8  # Reduce score if low confidence
            reasons.append(f"(prediction confidence: {confidence:.0%})")
    
    else:
        # Fallback to basic heuristics if ML fails
        reasons.append("Using basic nutrition heuristics (ML unavailable)")
        calories = _get_macro(recipe, "calories")
        protein = _get_macro(recipe, "protein_g")
        
        if energy == "low" and calories and calories <= 550:
            score += 0.2
        if protein and protein >= 20:
            score += 0.2
    
    # Normalize to [-1, 1]
    final_score = max(-1.0, min(1.0, score))
    explanation = "; ".join(reasons) if reasons else "Mood/energy neutral"
    
    # Debug info
    debug = {
        "mood": mood,
        "energy": energy,
        "ml_mood_prediction": mood_result if mood_result else None,
        "ml_energy_prediction": energy_result if energy_result else None,
        "ml_confidence": confidence if mood_result and energy_result else 0.0,
        "score": final_score,
        "nutrition_data": nutrition_data,
    }
    
    return final_score, explanation, debug


# ============================================================================
# STEP 3: Alternative - Separate mood and energy functions
# ============================================================================

"""
OR, if you prefer separate functions, use these instead:
"""

def compute_mood_score(recipe: Any, constraints: UserConstraints) -> tuple[float, str, dict]:
    """ML-based mood score in [0, 1]."""
    mood = (constraints.mood or "").lower()
    
    nutrition_data = {
        'calories': _get_macro(recipe, "calories"),
        'protein_g': _get_macro(recipe, "protein_g"),
        'carbs_g': _get_macro(recipe, "carbs_g"),
        'fat_g': _get_macro(recipe, "fat_g"),
        'sugar_g': _get_macro(recipe, "sugar_g"),
    }
    
    mood_result, _ = predict_both(nutrition_data)
    
    if not mood_result:
        return 0.5, "No prediction available", {}
    
    base_score = mood_result['score']
    reasons = []
    
    # Adjust based on user mood
    if mood in ["low", "stressed", "anxious"]:
        if mood_result['label'].lower() == "happy":
            base_score *= 1.2
            reasons.append("mood-boosting")
    elif mood in ["comfort", "cozy"]:
        if mood_result['label'].lower() in ["neutral", "happy"]:
            base_score *= 1.1
            reasons.append("comforting")
    
    final_score = min(1.0, base_score)
    explanation = f"Predicted {mood_result['label']} mood; " + "; ".join(reasons)
    
    debug = {
        "mood_prediction": mood_result,
        "score": final_score,
    }
    
    return final_score, explanation, debug


def compute_energy_score(recipe: Any, constraints: UserConstraints) -> tuple[float, str, dict]:
    """ML-based energy score in [0, 1]."""
    energy = (constraints.energy_level or "").lower()
    
    nutrition_data = {
        'calories': _get_macro(recipe, "calories"),
        'protein_g': _get_macro(recipe, "protein_g"),
        'carbs_g': _get_macro(recipe, "carbs_g"),
        'fat_g': _get_macro(recipe, "fat_g"),
        'sugar_g': _get_macro(recipe, "sugar_g"),
    }
    
    _, energy_result = predict_both(nutrition_data)
    
    if not energy_result:
        return 0.5, "No prediction available", {}
    
    base_score = energy_result['score']
    reasons = []
    
    # Adjust based on user energy
    if energy == "low":
        if energy_result['label'].lower() == "energy burst":
            base_score *= 1.3
            reasons.append("energizing")
    elif energy == "high":
        if energy_result['label'].lower() == "normal":
            base_score *= 1.1
            reasons.append("sustaining")
    
    final_score = min(1.0, base_score)
    explanation = f"Predicted {energy_result['label']} energy; " + "; ".join(reasons)
    
    debug = {
        "energy_prediction": energy_result,
        "score": final_score,
    }
    
    return final_score, explanation, debug


# ============================================================================
# STEP 4: Update score_recipes() to use the new functions
# ============================================================================

"""
In the score_recipes() function, the mood/energy scoring section should look like:
"""

# ... existing code ...

# Mood/Energy score: ML-based predictions
mood_energy_score, mood_energy_explanation, mood_energy_debug = compute_mood_energy_score(recipe, constraints)

# OR if using separate functions:
# mood_score, mood_explanation, mood_debug = compute_mood_score(recipe, constraints)
# energy_score, energy_explanation, energy_debug = compute_energy_score(recipe, constraints)
# combined_score = (mood_score + energy_score) / 2

# ... rest of scoring code ...


# ============================================================================
# STEP 5: Update debug info to include ML predictions
# ============================================================================

"""
In the debug dictionary construction:
"""

debug = {
    "coverage_score": coverage_score,
    "expiring_score": expiring_score,
    "nutrition_score": nutrition_score,
    "mood_energy_score": mood_energy_score,
    "total_score": final_score,
    
    # Add ML-specific debug info
    "ml_predictions": {
        "mood": mood_energy_debug.get("ml_mood_prediction"),
        "energy": mood_energy_debug.get("ml_energy_prediction"),
        "confidence": mood_energy_debug.get("ml_confidence"),
        "data_quality": mood_energy_debug.get("ml_mood_prediction", {}).get("data_quality"),
    },
    
    "nutrition_debug": nutrition_debug,
    "mood_energy_debug": mood_energy_debug,
}


# ============================================================================
# STEP 6: Enhance explanation with ML insights
# ============================================================================

"""
Update the explanation generation to mention ML predictions:
"""

explanation_parts = []

if expiring_score > 0.5:
    explanation_parts.append("uses ingredients that are expiring soon")

if coverage_score > 0.7:
    explanation_parts.append("relies mostly on what you already have")

if nutrition_score > 0.3:
    explanation_parts.append("matches your nutrition goal")

# Add ML-based insights
if mood_energy_debug.get("ml_mood_prediction"):
    mood_pred = mood_energy_debug["ml_mood_prediction"]
    if mood_pred['confidence'] > 0.8:
        explanation_parts.append(f"predicted to have a {mood_pred['label'].lower()} mood effect")

if mood_energy_debug.get("ml_energy_prediction"):
    energy_pred = mood_energy_debug["ml_energy_prediction"]
    if energy_pred['confidence'] > 0.8:
        explanation_parts.append(f"expected to provide {energy_pred['label'].lower()}")

if not explanation_parts:
    explanation_parts.append("is a balanced option for your current needs")

explanation = "This recipe " + ", ".join(explanation_parts) + "."


# ============================================================================
# COMPLETE EXAMPLE
# ============================================================================

"""
Here's a complete example showing all the changes in context:
"""

def complete_example():
    # At top of file
    from ml.mood_energy_model import predict_both
    
    # In score_recipes function
    def score_recipes(recipes, pantry_items, constraints):
        # ... existing code ...
        
        for recipe in recipes:
            # ... hard filters ...
            
            # Compute scores
            coverage_score = # ... existing ...
            expiring_score, matched_expiring = compute_expiring_score(recipe, pantry_items)
            nutrition_score, nutrition_explanation, nutrition_debug = compute_nutrition_score(recipe, constraints)
            
            # NEW: ML-based mood/energy scoring
            mood_energy_score, mood_energy_explanation, mood_energy_debug = compute_mood_energy_score(recipe, constraints)
            
            # Composite score
            final_score = (
                SCORE_WEIGHTS["coverage"] * coverage_score
                + SCORE_WEIGHTS["expiring"] * expiring_score
                + SCORE_WEIGHTS["nutrition"] * nutrition_score
                + SCORE_WEIGHTS["mood_energy"] * mood_energy_score
            )
            
            # Build explanation with ML insights
            explanation_parts = []
            if mood_energy_debug.get("ml_mood_prediction", {}).get("confidence", 0) > 0.7:
                mood_label = mood_energy_debug["ml_mood_prediction"]["label"]
                explanation_parts.append(f"predicted {mood_label.lower()} mood effect")
            
            # ... rest of function ...


# ============================================================================
# TESTING THE INTEGRATION
# ============================================================================

"""
After making these changes, test with:
"""

# 1. Start your backend server
# cd backend && uvicorn main:app --reload

# 2. Make a request to your existing chat endpoint
# curl -X POST http://localhost:8000/chat/recipes \
#   -H "Content-Type: application/json" \
#   -d '{
#     "message": "What can I make for dinner? I need something energizing.",
#     "mood": "low",
#     "energy_level": "low"
#   }'

# 3. Check the response - should now include ML predictions in debug info
# and better mood/energy scoring
