from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Any
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime
from database import get_session
from models import UserMealLog, Recipe, RecipeIngredient, Item, UserConstraints, UserProfile
from recommender import recommend_recipes_mvp
from ml.mood_energy_model import predict_both

router = APIRouter(prefix="/chat", tags=["chat"])


class WhatCanIMakeRequest(BaseModel):
    user_id: Optional[int] = None
    limit: int = 5
    expiring_soon_days: int = 3


class RecommendedRecipe(BaseModel):
    recipe_id: int
    title: Optional[str] = None
    score: float = 0.0
    missing_ingredients: Optional[List[str]] = None


@router.post("/what_can_i_make", response_model=List[RecommendedRecipe])
def what_can_i_make(payload: WhatCanIMakeRequest, session: Session = Depends(get_session)):
    """
    Return top-N recipe recommendations based on the pantry (and expiring items).
    Fetches recipes and pantry items from the database, then calls recommend_recipes_mvp.
    """
    try:
        # 1) Load ALL recipes from the database
        recipes = session.exec(select(Recipe)).all()
        recipe_payloads = []
        for r in recipes:
            ing_names = [ri.name for ri in r.ingredients] if r.ingredients else []
            recipe_payloads.append({
                "id": r.id,
                "title": r.title,
                "ingredients": ing_names,
                "time_minutes": r.time_minutes,
                "diet": r.diet,
                "cuisine": getattr(r, "cuisine", None),
                "avg_rating": getattr(r, "avg_rating", None),
            })
        
        # 2) Load ALL items (pantry)
        items = session.exec(select(Item)).all()
        pantry_names = [item.name for item in items]
        
        # 3) Create minimal constraints (no filters for now)
        constraints = UserConstraints()
        
        # 4) Create minimal user profile
        user_profile = UserProfile()
        
        # 5) Call the recommender
        recs = recommend_recipes_mvp(
            recipes=recipe_payloads,
            pantry_item_names=pantry_names,
            constraints=constraints,
            user_profile=user_profile,
            top_k=payload.limit,
        )
        
        # 6) Convert to RecommendedRecipe response model
        results: List[RecommendedRecipe] = []
        for r in recs:
            results.append(RecommendedRecipe(
                recipe_id=r.get("id"),
                title=r.get("title"),
                score=0.0,  # recommender doesn't return a "score" field; use 0.0 or add one
                missing_ingredients=r.get("missing_ingredients"),
            ))
        return results
    except Exception as exc:
        # If recommender fails, return 501 so frontend knows to handle gracefully
        raise HTTPException(status_code=501, detail=f"Recommender unavailable: {str(exc)}")


class MealLogCreate(BaseModel):
    user_id: Optional[int] = None
    recipe_id: Optional[int] = None
    recipe_title: str  # required: the name of the recipe
    taste_rating: Optional[int] = None  # 1-5 rating
    liked_tags: Optional[List[str]] = None
    disliked_tags: Optional[List[str]] = None
    feel_after: Optional[str] = None
    notes: Optional[str] = None
    cooked_at: Optional[datetime] = None


# --- Chat Recipes Models ---
class ChatRecipesRequest(BaseModel):
    mood: Optional[str] = None
    energy: Optional[str] = None
    diet: Optional[str] = None
    include_ingredients: Optional[List[str]] = None
    exclude_ingredients: Optional[List[str]] = None
    max_time_minutes: Optional[int] = None
    nutrition_goal: Optional[str] = None


class RecipeSuggestion(BaseModel):
    recipe_id: int
    title: str
    reason: str
    time_minutes: Optional[int] = None
    mood_effect: Optional[str] = None
    explanation: Optional[str] = None
    debug: Optional[dict] = None


class ChatRecipesResponse(BaseModel):
    reply: str
    recipes: List[RecipeSuggestion]


# --- Helper Functions ---

# Nutrition goal thresholds used for scoring
NUTRITION_THRESHOLDS = {
    "high_protein": {"protein_g": 30},
    "low_carb": {"carbs_g": 35},
    "low_calorie": {"calories": 550},
}


def infer_nutrition_goal(constraints: UserConstraints) -> Optional[str]:
    """Derive a nutrition goal from explicit request, macro hints, or energy level."""
    explicit_goal = getattr(constraints, "nutrition_goal", None)
    if explicit_goal:
        return explicit_goal

    macro_hint = getattr(constraints, "prioritize_macro", None)
    if macro_hint in ["high_protein", "low_carb", "low_calorie"]:
        return macro_hint

    energy = (constraints.energy_level or "").lower()
    if energy == "high":
        return "high_protein"
    if energy == "low":
        return "low_calorie"
    return None


def _get_macro(recipe: Any, key: str) -> Optional[float]:
    """Fetch macro from recipe supporting both base and nutrition_* fields."""
    value = getattr(recipe, key, None)
    if value is not None:
        return value
    alt_key = f"nutrition_{key}"
    return getattr(recipe, alt_key, None)


def parse_constraints_from_message(message: str) -> UserConstraints:
    """
    Extract simple constraints from a natural language message.
    Looks for keywords like: high protein, light, quick, under 30 minutes, vegan, vegetarian, etc.
    Returns a UserConstraints object with populated fields.
    """
    message_lower = message.lower()
    constraints = UserConstraints()

    # Time constraints
    if "quick" in message_lower or "fast" in message_lower:
        constraints.max_time_minutes = 20
    elif "under 30" in message_lower or "30 minutes" in message_lower:
        constraints.max_time_minutes = 30
    elif "under 20" in message_lower or "20 minutes" in message_lower:
        constraints.max_time_minutes = 20

    # Diet constraints
    if "vegan" in message_lower:
        constraints.diet_types = ["vegan"]
    elif "vegetarian" in message_lower:
        constraints.diet_types = ["vegetarian"]
    elif "pescatarian" in message_lower:
        constraints.diet_types = ["pescatarian"]

    # Protein constraint (stored as include_ingredients for now)
    if "high protein" in message_lower or "protein" in message_lower:
        # Prefer recipes that are high in protein; also prefer common protein ingredients
        constraints.include_ingredients = ["protein", "chicken", "fish", "beef", "tofu", "beans", "eggs"]
        constraints.prioritize_ingredient = "protein"

    # Carb constraints
    if "high carb" in message_lower or "high-carbs" in message_lower or "high carbs" in message_lower:
        constraints.prioritize_macro = "high_carb"
    if "low carb" in message_lower or "low-carb" in message_lower or "low carbs" in message_lower:
        constraints.prioritize_macro = "low_carb"

    # Light/healthy constraint
    if "light" in message_lower or "healthy" in message_lower:
        constraints.exclude_ingredients = ["cream", "butter", "oil"]

    # Keto diet
    if "keto" in message_lower or "ketogenic" in message_lower:
        constraints.diet_types = ["keto"]
    
    # Gluten-free
    if "gluten" in message_lower or "gluten-free" in message_lower or "gluten free" in message_lower:
        constraints.exclude_ingredients = (constraints.exclude_ingredients or []) + ["gluten", "wheat", "bread"]

    # Expiring preference with configurable window
    import re
    expiring_window_days = 3  # default
    expiring_match = re.search(r"expiring\s+in\s+(\d+)\s+days?", message_lower)
    if expiring_match:
        try:
            expiring_window_days = int(expiring_match.group(1))
        except ValueError:
            expiring_window_days = 3
    
    if "expiring" in message_lower or "use expiring" in message_lower or "use soon" in message_lower or "use up" in message_lower:
        constraints.prioritize_ingredient = "expiring"
    
    # Store the expiring window for score_recipes to use
    constraints._expiring_window_days = expiring_window_days

    # Explicit include/exclude phrases with improved regex patterns
    # Includes: "use X", "include X", "with X", "make with X", "recipe with X", "what can i make with X"
    include_patterns = [
        r"(?:use|include|want|need)\s+([a-z0-9,\s&\-]+?)(?:\s+(?:and|or|please|recipe|to make|with)|\?|$)",
        r"(?:make with|recipe with|what\s+can\s+i\s+make\s+with)\s+([a-z0-9,\s&\-]+?)(?:\s+(?:and|or|please|no|don't|exclude|without|allergic|dislike)|\?|$)",
    ]
    # Separate pattern for "with X" to avoid capturing whole phrases
    with_pattern = r"(?:^|\s)with\s+([a-z0-9,\s&\-]+?)(?:\s+(?:and|or|please|no|don't|exclude|without|allergic|dislike)|\?|$)"
    
    for pattern in include_patterns:
        for m in re.finditer(pattern, message_lower):
            items_str = m.group(1).strip()
            parts = re.split(r",|\s+and\s+|\s+or\s+|\s+with\s+", items_str)
            parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1 and p.strip() not in ["something", "everything", "make", "a", "an"]]
            if parts:
                constraints.include_ingredients = (constraints.include_ingredients or []) + parts
    
    # Handle "with X" pattern separately
    for m in re.finditer(with_pattern, message_lower):
        items_str = m.group(1).strip()
        parts = re.split(r",|\s+and\s+|\s+or\s+", items_str)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1 and p.strip() not in ["something", "everything"]]
        if parts:
            constraints.include_ingredients = (constraints.include_ingredients or []) + parts

    # Excludes: "no X", "don't use X", "allergic to X", "can't have X", "exclude X", "without X", "dislike X"
    # Use lookahead to find phrase boundaries, stopping at commas, phrase repetitions, or other keywords
    exclude_patterns = [
        r"(?:no|don't use|dont use|can't have|cannot have|allergic to|dislike|exclude|without)\s+([a-z0-9,\s&\-]+?)(?=,|and\s+(?:no|don't|allergic|exclude|dislike|without)|make|recipe|with|use|\?|$)",
    ]
    for pattern in exclude_patterns:
        for m in re.finditer(pattern, message_lower):
            items_str = m.group(1).strip()
            parts = re.split(r",|\s+and\s+|\s+or\s+", items_str)
            parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
            if parts:
                constraints.exclude_ingredients = (constraints.exclude_ingredients or []) + parts
    
    # Deduplicate and clean up lists
    if constraints.include_ingredients:
        constraints.include_ingredients = list(set(constraints.include_ingredients))
    if constraints.exclude_ingredients:
        constraints.exclude_ingredients = list(set(constraints.exclude_ingredients))

    return constraints


def compute_nutrition_score(recipe: Any, constraints: UserConstraints) -> tuple[float, str, dict]:
    """
    Compute a nutrition match score in [-1, 1] using goal-based thresholds.

    Returns (score, explanation, debug) to feed into downstream debug plumbing.
    """
    goal = infer_nutrition_goal(constraints)
    debug = {
        "goal": goal,
        "thresholds": NUTRITION_THRESHOLDS.get(goal) if goal else None,
        "macros": {},
        "components": {},
        "missing_macros": [],
    }

    if not goal or goal not in NUTRITION_THRESHOLDS:
        return 0.0, "No nutrition goal specified", debug

    thresholds = NUTRITION_THRESHOLDS[goal]
    direction = "high" if goal == "high_protein" else "low"

    component_scores: List[float] = []
    reasons = []

    for macro_key, target in thresholds.items():
        value = _get_macro(recipe, macro_key)
        debug["macros"][macro_key] = value

        if value is None:
            debug["missing_macros"].append(macro_key)
            continue

        if direction == "high":
            if value >= target * 1.3:
                comp = 1.0
                reasons.append(f"{macro_key} {int(value)}g is well above {target}g goal")
            elif value >= target:
                comp = 0.6
                reasons.append(f"{macro_key} {int(value)}g meets {target}g goal")
            else:
                comp = -0.5
                reasons.append(f"{macro_key} {int(value)}g is below {target}g goal")
        else:
            if value <= target * 0.7:
                comp = 1.0
                reasons.append(f"{macro_key} {int(value)} is well under {target} limit")
            elif value <= target:
                comp = 0.4
                reasons.append(f"{macro_key} {int(value)} is under {target} limit")
            else:
                comp = -0.6
                reasons.append(f"{macro_key} {int(value)} exceeds {target} limit")

        debug["components"][macro_key] = comp
        component_scores.append(comp)

    if not component_scores:
        return 0.0, "No nutrition data on recipe", debug

    avg_score = sum(component_scores) / len(component_scores)
    final_score = max(-1.0, min(1.0, avg_score))
    explanation = "; ".join(reasons) if reasons else "Nutrition goal considered"
    debug["score"] = final_score
    return final_score, explanation, debug


def compute_mood_energy_score(recipe: Any, constraints: UserConstraints) -> tuple[float, str, dict]:
    """ML-powered mood/energy alignment score in [-1, 1] with heuristic fallback."""
    mood = (constraints.mood or "").lower()
    energy = (constraints.energy_level or "").lower()
    calories = _get_macro(recipe, "calories")
    fat = _get_macro(recipe, "fat_g")
    protein = _get_macro(recipe, "protein_g")
    carbs = _get_macro(recipe, "carbs_g")
    sugar = _get_macro(recipe, "sugar_g")
    time_minutes = getattr(recipe, "time_minutes", None)

    score = 0.0
    reasons: List[str] = []
    debug = {
        "mood": mood,
        "energy": energy,
        "calories": calories,
        "fat_g": fat,
        "protein_g": protein,
        "carbs_g": carbs,
        "sugar_g": sugar,
        "time_minutes": time_minutes,
        "ml_used": False,
    }

    # Try ML predictions first if we have enough nutrition data
    if calories is not None:
        try:
            nutrition_data = {
                "calories": calories,
            }
            if protein is not None:
                nutrition_data["protein_g"] = protein
            if carbs is not None:
                nutrition_data["carbs_g"] = carbs
            if fat is not None:
                nutrition_data["fat_g"] = fat
            if sugar is not None:
                nutrition_data["sugar_g"] = sugar
            
            # Get ML predictions
            mood_result, energy_result = predict_both(nutrition_data)
            
            # Store ML results in debug
            debug["ml_used"] = True
            debug["ml_mood"] = mood_result
            debug["ml_energy"] = energy_result
            
            # Map ML predictions to scores based on user request
            ml_score = 0.0
            
            # Mood mapping (Happy=positive, Sad=negative, Neutral=0)
            if mood:
                mood_label = mood_result["label"].lower()
                mood_confidence = mood_result["confidence"]
                
                if mood in ["comfort", "cozy", "hearty", "happy", "good"]:
                    if mood_label == "happy":
                        ml_score += 0.5 * mood_confidence
                        reasons.append(f"ML predicts {mood_label} mood (conf: {mood_confidence:.0%})")
                    elif mood_label == "sad":
                        ml_score -= 0.3 * mood_confidence
                        reasons.append(f"ML predicts {mood_label} mood - may not match comfort request")
                elif mood in ["light", "fresh", "healthy"]:
                    if mood_label == "neutral" or mood_label == "happy":
                        ml_score += 0.3 * mood_confidence
                        reasons.append(f"ML predicts {mood_label} mood - good for light meal")
                else:
                    # Neutral mood request or unrecognized
                    if mood_label == "neutral":
                        ml_score += 0.2 * mood_confidence
                        reasons.append(f"ML predicts neutral mood")
            
            # Energy mapping (Energy Burst=high, Low=low, Normal=medium)
            if energy:
                energy_label = energy_result["label"].lower()
                energy_confidence = energy_result["confidence"]
                
                if energy == "low":
                    if "low" in energy_label or "normal" in energy_label:
                        ml_score += 0.4 * energy_confidence
                        reasons.append(f"ML predicts {energy_label} energy (conf: {energy_confidence:.0%})")
                    else:
                        ml_score -= 0.2 * energy_confidence
                        reasons.append(f"ML predicts {energy_label} - may be too energizing")
                elif energy == "high":
                    if "burst" in energy_label or "energy" in energy_label:
                        ml_score += 0.5 * energy_confidence
                        reasons.append(f"ML predicts {energy_label} (conf: {energy_confidence:.0%})")
                    elif "normal" in energy_label:
                        ml_score += 0.2 * energy_confidence
                        reasons.append(f"ML predicts {energy_label} energy")
                else:
                    # Medium/normal energy or unspecified
                    if "normal" in energy_label:
                        ml_score += 0.3 * energy_confidence
                        reasons.append(f"ML predicts {energy_label} energy")
            
            # Use ML score if we got predictions
            if ml_score != 0.0:
                score = ml_score
                
        except Exception as e:
            # ML prediction failed, fall back to heuristics
            debug["ml_error"] = str(e)
            debug["ml_used"] = False
    
    # Fallback to heuristics if ML wasn't used or gave no score
    if not debug["ml_used"] or score == 0.0:
        # Energy-driven hints (heuristic fallback)
        if energy == "low":
            if calories is not None and calories <= 550:
                score += 0.3
                reasons.append("lighter on calories for low energy")
            if time_minutes and time_minutes <= 30:
                score += 0.1
                reasons.append("quick prep for low energy")
        elif energy == "high":
            if protein is not None and protein >= 25:
                score += 0.3
                reasons.append("higher protein for high energy")
            elif protein is not None and protein >= 15:
                score += 0.1
                reasons.append("moderate protein for energy")

        # Mood-driven hints (heuristic fallback)
        if mood in ["comfort", "cozy", "hearty"]:
            if calories is not None and calories >= 650:
                score += 0.3
                reasons.append("comforting calories")
            else:
                score -= 0.1
                reasons.append("may be lighter than comfort craving")
        elif mood in ["light", "fresh", "healthy"]:
            if calories is not None and calories <= 550 and (fat is None or fat <= 20):
                score += 0.3
                reasons.append("light profile")
            else:
                score -= 0.1
                reasons.append("may be heavier than requested light mood")
        elif mood in ["focus", "post-workout", "gym", "muscle"]:
            if protein is not None and protein >= 25:
                score += 0.3
                reasons.append("protein to support focus/recovery")
            else:
                score -= 0.1
                reasons.append("may need more protein for focus/recovery")

    final_score = max(-1.0, min(1.0, score))
    explanation = "; ".join(reasons) if reasons else "Mood/energy neutral"
    debug["score"] = final_score
    return final_score, explanation, debug


def compute_expiring_score(
    recipe: Any,
    pantry_items: List[Item],
) -> tuple[float, List[str]]:
    """
    Compute expiring items score in [0, 1] and return matched expiring ingredients.
    
    Uses two windows:
    - Urgent: 0-7 days → weight 1.0
    - Soon: 7-14 days → weight 0.5
    
    Score = sum(weights for matching expiring pantry items) / total recipe ingredients
    
    Args:
        recipe: Recipe object with ingredients list
        pantry_items: List of Item objects (may have expiration_date)
    
    Returns:
        (score in [0, 1], matched expiring ingredient names)
    """
    from datetime import date
    
    ing_names = [ri.name.lower() for ri in recipe.ingredients] if recipe.ingredients else []
    if not ing_names:
        return 0.0, []
    
    # Build pantry item map with expiry windows
    pantry_map = {}  # {name_lower: weight}
    today = date.today()
    
    for item in pantry_items:
        item_name = item.name.lower()
        exp_date = getattr(item, "expiration_date", None)
        if not exp_date:
            continue
        
        try:
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date).date()
            
            if isinstance(exp_date, date):
                delta = (exp_date - today).days
                if 0 <= delta <= 7:
                    pantry_map[item_name] = 1.0  # Urgent
                elif 7 < delta <= 14:
                    pantry_map[item_name] = 0.5  # Soon
        except Exception:
            pass  # Ignore malformed dates
    
    # Match recipe ingredients with expiring pantry items (substring/token matching)
    total_weight = 0.0
    matched_expiring: List[str] = []
    for ing in ing_names:
        for pantry_name, weight in pantry_map.items():
            # Use substring matching: pantry_name is substring of ing or vice versa
            if pantry_name in ing or ing in pantry_name:
                total_weight += weight
                matched_expiring.append(pantry_name)
                break  # Count each ingredient once per recipe
    
    expiring_score = total_weight / len(ing_names)
    return min(1.0, expiring_score), matched_expiring  # Cap at 1.0


def score_recipes(
    recipes: List[Any],
    pantry_items: List[Item],
    constraints: UserConstraints,
) -> List[dict]:
    """
    Score and filter recipes in two stages:
    
    1. HARD FILTERS: Time, diet, include/exclude ingredients
       - Any recipe not passing these is discarded (no score computed).
    
    2. SOFT SCORING (applied to candidates only):
       - expiring_score: [0, 1] how many recipe ingredients are expiring
       - coverage_score: [0, 1] what fraction of recipe ingredients are in pantry
       - nutrition_score: [-1, 1] how well recipe matches nutrition hints
       
       Final score is weighted combination of these subscores.
    
    Returns:
        List of dicts: {recipe, recipe_id, title, score, reasons}
        (sorted by score descending)
    """
    from datetime import date
    
    # === SETUP ===
    pantry_items_map = {item.name.lower(): item for item in pantry_items}
    scored_recipes = []
    
    # Configurable scoring weights (can be exposed as constants later)
    # Increased mood_energy weight since we now have ML predictions
    SCORE_WEIGHTS = {
        "coverage": 0.30,
        "expiring": 0.25,
        "nutrition": 0.20,
        "mood_energy": 0.25,  # Increased from 0.15 to 0.25 with ML
    }
    
    # === FILTER & SCORE ===
    for recipe in recipes:
        recipe_id = recipe.id
        title = recipe.title
        time_minutes = recipe.time_minutes
        diet_tag = recipe.diet
        
        # Get recipe ingredients (normalized to lowercase)
        ing_names = [ri.name.lower() for ri in recipe.ingredients] if recipe.ingredients else []
        if not ing_names:
            continue  # Skip recipes with no ingredients
        
        # --- HARD FILTER 1: Time constraint ---
        if constraints.max_time_minutes and time_minutes:
            if time_minutes > constraints.max_time_minutes:
                continue  # Skip: exceeds time limit
        
        # --- HARD FILTER 2: Diet constraint (with inference) ---
        if constraints.diet_types:
            allowed_diets = {d.lower() for d in constraints.diet_types}
            
            # Check explicit diet tag first
            if diet_tag and diet_tag.lower() in allowed_diets:
                pass  # Passes filter
            else:
                # Infer diet from ingredients
                meat_keywords = ['chicken', 'beef', 'pork', 'lamb', 'turkey', 'bacon', 'sausage', 'meat']
                fish_keywords = ['fish', 'salmon', 'tuna', 'shrimp', 'seafood', 'cod', 'tilapia']
                dairy_keywords = ['milk', 'cheese', 'butter', 'cream', 'yogurt']
                
                has_meat = any(any(kw in ing for kw in meat_keywords) for ing in ing_names)
                has_fish = any(any(kw in ing for kw in fish_keywords) for ing in ing_names)
                has_dairy = any(any(kw in ing for kw in dairy_keywords) for ing in ing_names)
                
                # Infer diet type
                inferred_diet = None
                if not has_meat and not has_fish and not has_dairy:
                    inferred_diet = 'vegan'
                elif not has_meat and not has_fish:
                    inferred_diet = 'vegetarian'
                elif not has_meat and has_fish:
                    inferred_diet = 'pescatarian'
                
                # Check if inferred diet matches requested diet
                if not (inferred_diet and inferred_diet in allowed_diets):
                    continue  # Skip: diet does not match
        
        # --- HARD FILTER 3: Must include ingredients ---
        if constraints.include_ingredients:
            include_set = {i.lower() for i in constraints.include_ingredients}
            all_found = True
            for required in include_set:
                # Use substring matching (same as expiring & exclude)
                found = any(required in ing or ing in required for ing in ing_names)
                if not found:
                    all_found = False
                    break
            if not all_found:
                continue  # Skip this recipe (missing required ingredient)
        
        # --- HARD FILTER 4: Must exclude ingredients ---
        if constraints.exclude_ingredients:
            exclude_set = {e.lower() for e in constraints.exclude_ingredients}
            skip_recipe = False
            for ing in ing_names:
                if any(exc in ing or ing in exc for exc in exclude_set):
                    skip_recipe = True
                    break
            if skip_recipe:
                continue  # Skip: contains excluded ingredient
        
        # === RECIPE PASSED ALL HARD FILTERS: NOW COMPUTE SOFT SCORES ===
        
        # Pantry coverage score: what fraction of ingredients do we have?
        have_count = sum(
            1 for ing in ing_names
            if any(ing in pname or pname in ing for pname in pantry_items_map)
        )
        coverage_score = have_count / len(ing_names)
        
        # Expiring items score: how many expiring ingredients does it use?
        expiring_score, matched_expiring = compute_expiring_score(recipe, pantry_items)
        
        # Nutrition score: does it match diet/energy hints?
        nutrition_score, nutrition_explanation, nutrition_debug = compute_nutrition_score(recipe, constraints)

        # Mood/Energy score: align with mood keywords and energy level hints
        mood_energy_score, mood_energy_explanation, mood_energy_debug = compute_mood_energy_score(recipe, constraints)
        
        # --- COMPOSITE SCORE ---
        final_score = (
            SCORE_WEIGHTS["coverage"] * coverage_score
            + SCORE_WEIGHTS["expiring"] * expiring_score
            + SCORE_WEIGHTS["nutrition"] * nutrition_score
            + SCORE_WEIGHTS["mood_energy"] * mood_energy_score
        )
        
        # --- BUILD REASON STRING ---
        reasons = []
        if coverage_score >= 0.7:
            reasons.append(f"has {int(coverage_score*100)}% of ingredients")
        if expiring_score >= 0.3:
            reasons.append("uses expiring items")
        if time_minutes:
            reasons.append(f"Quick ({time_minutes} min)")
        if diet_tag or constraints.diet_types:
            reasons.append(f"{diet_tag or 'Matching diet'}")
        if nutrition_score > 0:
            reasons.append("fits nutrition goal")
        if mood_energy_score > 0:
            reasons.append("matches mood/energy")

        reason_str = ", ".join(reasons) if reasons else "Good match"

        explanation_parts = []
        if coverage_score:
            explanation_parts.append(f"Pantry coverage: {int(coverage_score * 100)}%")
        if matched_expiring:
            explanation_parts.append(f"Uses expiring: {', '.join(sorted(set(matched_expiring)))}")
        if nutrition_explanation:
            explanation_parts.append(nutrition_explanation)
        if mood_energy_explanation:
            explanation_parts.append(mood_energy_explanation)
        explanation = "; ".join(explanation_parts)

        debug = {
            "weights": SCORE_WEIGHTS,
            "coverage": {
                "score": coverage_score,
                "matched": have_count,
                "total": len(ing_names),
            },
            "expiring": {
                "score": expiring_score,
                "matched": matched_expiring,
            },
            "nutrition": {
                "score": nutrition_score,
                "explanation": nutrition_explanation,
                **nutrition_debug,
            },
            "mood_energy": {
                "score": mood_energy_score,
                "explanation": mood_energy_explanation,
                **mood_energy_debug,
            },
        }
        
        scored_recipes.append({
            "recipe": recipe,
            "recipe_id": recipe_id,
            "title": title,
            "score": final_score,
            "coverage": coverage_score,
            "expiring": expiring_score,
            "nutrition": nutrition_score,
            "mood_energy": mood_energy_score,
            "time_minutes": time_minutes,
            "reason": reason_str,
            "explanation": explanation,
            "debug": debug,
        })
    
    # === SORT BY FINAL SCORE (DESCENDING) ===
    scored_recipes.sort(key=lambda x: x["score"], reverse=True)
    return scored_recipes


@router.post("/log", response_model=UserMealLog)
def log_meal(payload: MealLogCreate, session: Session = Depends(get_session)):
    """
    Persist a UserMealLog entry (feedback after cooking).
    """
    import json
    cooked_at = payload.cooked_at or datetime.utcnow()
    log = UserMealLog(
        user_id=payload.user_id,
        recipe_id=payload.recipe_id,
        recipe_title=payload.recipe_title,
        taste_rating=payload.taste_rating,
        liked_tags=json.dumps(payload.liked_tags) if payload.liked_tags else None,
        disliked_tags=json.dumps(payload.disliked_tags) if payload.disliked_tags else None,
        feel_after=payload.feel_after,
        notes=payload.notes,
        cooked_at=cooked_at,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.get("/logs", response_model=List[UserMealLog])
def get_logs(session: Session = Depends(get_session)):
    """
    Retrieve all feedback logs (for debugging/viewing).
    """
    logs = session.exec(select(UserMealLog)).all()
    return logs


@router.post("/recipes", response_model=ChatRecipesResponse)
def chat_recipes(payload: ChatRecipesRequest, session: Session = Depends(get_session)):
    """
    Structured recipe recommendation endpoint.
    
    Takes structured criteria (diet, include/exclude ingredients, time, etc.)
    and returns matching recipe suggestions with reasons.
    """
    try:
        # 1) Build constraints from structured payload
        constraints = UserConstraints(
            diet_types=[payload.diet] if payload.diet else None,
            include_ingredients=payload.include_ingredients,
            exclude_ingredients=payload.exclude_ingredients,
            max_time_minutes=payload.max_time_minutes,
            mood=payload.mood,
            energy_level=payload.energy,
            nutrition_goal=payload.nutrition_goal,
        )
        
        # 2) Load recipes and pantry items from database
        recipes = session.exec(select(Recipe)).all()
        pantry_items = session.exec(select(Item)).all()
        
        if not recipes:
            return ChatRecipesResponse(
                reply="I didn't find any recipes in the database yet. Add some recipes first!",
                recipes=[]
            )
        
        if not pantry_items:
            return ChatRecipesResponse(
                reply="Your pantry is empty. Add some items and I'll suggest recipes that use them.",
                recipes=[]
            )
        
        # 3) Score recipes
        scored = score_recipes(recipes, pantry_items, constraints)
        
        # 4) Take top 3-5 recipes
        top_recipes = scored[:5]
        
        if not top_recipes:
            return ChatRecipesResponse(
                reply="I couldn't find recipes that match your criteria. Try different filters!",
                recipes=[]
            )
        
        # 5) Build response
        suggestions = []
        for item in top_recipes:
            suggestion = RecipeSuggestion(
                recipe_id=item["recipe_id"],
                title=item["title"],
                reason=item["reason"],
                time_minutes=item["time_minutes"],
                mood_effect=None,  # placeholder
                explanation=item.get("explanation"),
                debug=item.get("debug"),
            )
            suggestions.append(suggestion)
        
        # 6) Generate natural language reply
        num_recipes = len(suggestions)
        reply = f"I found {num_recipes} recipe(s) that match your request. "
        if constraints.max_time_minutes:
            reply += f"All are under {constraints.max_time_minutes} minutes. "
        if constraints.diet_types:
            reply += f"Based on your {', '.join(constraints.diet_types)} preference. "
        if constraints.nutrition_goal:
            reply += f"Prioritizing {constraints.nutrition_goal.replace('_', ' ')}. "
        reply += "Check them out below!"
        
        return ChatRecipesResponse(reply=reply, recipes=suggestions)
        
    except Exception as exc:
        return ChatRecipesResponse(
            reply=f"Error processing your request: {str(exc)}",
            recipes=[]
        )