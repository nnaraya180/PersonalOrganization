# recommender.py

from typing import Sequence, Optional, List, Dict, Any

from models import UserConstraints, UserProfile


# ---------- small internal helpers ----------

def _normalize_name(name: str) -> str:
    """Lowercase + strip for consistent matching."""
    return name.strip().lower()


def _get_field(obj: Any, field: str, default=None):
    """
    Read a field from either:
      - a dict: obj[field]
      - an object: getattr(obj, field)
    Falls back to default if not found.
    """
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _ensure_ingredient_list(raw_ingredients: Any) -> List[str]:
    """
    Convert ingredients into a clean list of strings.
    Supports:
      - list of strings
      - comma-separated string
    """
    if raw_ingredients is None:
        return []

    if isinstance(raw_ingredients, list):
        # assume already list of strings
        return [str(i) for i in raw_ingredients if i]

    # fallback: assume comma-separated string
    return [part.strip() for part in str(raw_ingredients).split(",") if part.strip()]


def _compute_pantry_coverage(
    recipe_ingredients: List[str],
    pantry_item_names: Sequence[str],
) -> float:
    """
    Fraction of recipe ingredients that are already in the pantry.
    Returns a value in [0, 1].
    """
    ing_set = {_normalize_name(i) for i in recipe_ingredients if i}
    if not ing_set:
        return 0.0

    pantry_set = {_normalize_name(n) for n in pantry_item_names}
    if not pantry_set:
        return 0.0

    overlap = ing_set & pantry_set
    return len(overlap) / len(ing_set)


def _compute_missing_ingredients(
    recipe_ingredients: List[str],
    pantry_item_names: Sequence[str],
) -> List[str]:
    """
    Return the ingredients from the recipe that are NOT in the pantry.
    Uses case-insensitive matching, but returns the original ingredient strings.
    """
    pantry_set = {_normalize_name(n) for n in pantry_item_names}
    missing: List[str] = []

    for ing in recipe_ingredients:
        if not ing:
            continue
        if _normalize_name(ing) not in pantry_set:
            missing.append(ing)

    return missing


def _compute_expiry_score_stub(
    recipe_ingredients: List[str],
    pantry_item_names: Sequence[str],
) -> float:
    """
    Placeholder for future 'use it up' logic based on expiration dates.
    For MVP, return a constant so it doesn't dominate but is present.
    """
    return 0.5


def _compute_mood_energy_term_stub(
    constraints: UserConstraints,
) -> float:
    """
    Placeholder for mood/energy alignment.

    For now, this returns 0.0 for all recipes, so it doesn't affect ranking.
    We still accept mood/energy in the interface, so later we can plug in
    a real model here without changing the function signature.
    """
    # Example sketch for the future:
    # - Map (constraints.mood, constraints.energy_level) to some target vector
    # - Use an ML model to estimate how well each recipe matches that target
    #
    # For true MVP: neutral.
    return 0.0


def _recipe_matches_cuisine(
    recipe_cuisine: Optional[str],
    allowed_cuisines: Sequence[str],
) -> bool:
    """
    Check if a recipe's cuisine matches any of the allowed cuisines.
    If the recipe has no cuisine, treat it as non-matching.
    """
    if recipe_cuisine is None:
        return False

    recipe_c = _normalize_name(recipe_cuisine)
    allowed = {_normalize_name(c) for c in allowed_cuisines}
    return recipe_c in allowed


def _recipe_has_all_includes(
    recipe_ingredients: List[str],
    include_ingredients: Sequence[str],
) -> bool:
    """
    True if the recipe contains ALL of the include_ingredients.
    """
    if not include_ingredients:
        return True  # nothing required

    ing_set = {_normalize_name(i) for i in recipe_ingredients if i}
    includes = {_normalize_name(i) for i in include_ingredients}
    return includes.issubset(ing_set)


def _recipe_has_excluded(
    recipe_ingredients: List[str],
    exclude_names: Sequence[str],
) -> bool:
    """
    True if the recipe contains ANY of the excluded ingredients.
    This is used for both explicit excludes and allergies.
    """
    if not exclude_names:
        return False

    ing_set = {_normalize_name(i) for i in recipe_ingredients if i}
    excluded = {_normalize_name(e) for e in exclude_names}
    return any(e in ing_set for e in excluded)


# ---------- main MVP recommender ----------

def recommend_recipes_mvp(
    recipes: Sequence[Any],
    pantry_item_names: Sequence[str],
    constraints: UserConstraints,
    user_profile: Optional[UserProfile] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    MVP recipe recommender.

    See previous discussion for detailed behavior.
    Returns a list of dicts with: title, missing_ingredients, cuisine, avg_rating.
    """

    pantry_item_names = list(pantry_item_names)  # ensure we can iterate multiple times

    # ---- 1) Build combined exclude list (allergies + explicit excludes) ----
    exclude_names: List[str] = []

    if constraints.exclude_ingredients:
        exclude_names.extend(constraints.exclude_ingredients)

    if user_profile is not None:
        if user_profile.allergies:
            exclude_names.extend(user_profile.allergies)
        # For MVP, user_profile.diet_types is not implemented as a filter yet.

    # ---- 2) Filter recipes based on constraints & profile ----

    candidates: List[Dict[str, Any]] = []

    for recipe in recipes:
        title = _get_field(recipe, "title")
        raw_ingredients = _get_field(recipe, "ingredients", None)
        cuisine = _get_field(recipe, "cuisine", None)
        avg_rating = _get_field(recipe, "avg_rating", None)

        # NEW: pull id, time, diet from the recipe dicts your endpoint passes
        recipe_id = _get_field(recipe, "id", None)
        time_minutes = _get_field(recipe, "time_minutes", None)
        diet = _get_field(recipe, "diet", None)

        # If no title or ingredients, skip (data is incomplete)
        if title is None or raw_ingredients is None:
            continue

        ingredients = _ensure_ingredient_list(raw_ingredients)

        # 2a) Cuisine filter (if specified)
        if constraints.cuisine:
            if not _recipe_matches_cuisine(cuisine, constraints.cuisine):
                continue

        # 2b) Include ingredients: recipe must contain ALL of them
        if constraints.include_ingredients:
            if not _recipe_has_all_includes(ingredients, constraints.include_ingredients):
                continue

        # 2c) Exclude ingredients + allergies
        if _recipe_has_excluded(ingredients, exclude_names):
            continue

        # 2d) Max time filter
        if constraints.max_time_minutes is not None and time_minutes is not None:
            if time_minutes > constraints.max_time_minutes:
                continue

        # 2e) Diet filter using diet_types (if provided)
        if constraints.diet_types:
            allowed_diets = {_normalize_name(d) for d in constraints.diet_types if d}
            if diet is None or _normalize_name(diet) not in allowed_diets:
                continue

        # If we got here, the recipe passes all hard filters.
        candidates.append(
            {
                "recipe": recipe,
                "id": recipe_id,
                "title": title,
                "ingredients": ingredients,
                "cuisine": cuisine,
                "diet": diet,
                "time_minutes": time_minutes,
                "avg_rating": avg_rating,
            }
        )


    if not candidates:
        return []  # no viable recipes

    # ---- 3) Compute scores for each candidate ----

    mood_energy_term = _compute_mood_energy_term_stub(constraints)

    for cand in candidates:
        ingredients = cand["ingredients"]

        pantry_coverage = _compute_pantry_coverage(ingredients, pantry_item_names)
        expiry_score = _compute_expiry_score_stub(ingredients, pantry_item_names)

        # MVP scoring: pantry + expiry + mood/energy placeholder
        raw_score = (
            0.6 * pantry_coverage +
            0.4 * expiry_score +
            0.0 * mood_energy_term  # placeholder; doesn't affect ranking yet
        )

        cand["pantry_coverage"] = pantry_coverage
        cand["expiry_score"] = expiry_score
        cand["raw_score"] = raw_score

    # ---- 4) Normalize raw_score to [-1, 1] ----

    raw_scores = [c["raw_score"] for c in candidates]
    min_raw = min(raw_scores)
    max_raw = max(raw_scores)

    if max_raw == min_raw:
        # All the same → treat as neutral
        for c in candidates:
            c["final_score"] = 0.0
    else:
        for c in candidates:
            c["final_score"] = (
                2 * (c["raw_score"] - min_raw) / (max_raw - min_raw) - 1
            )

    # ---- 5) Sort by final_score and build output ----

    results: List[Dict[str, Any]] = []

    for c in candidates[:top_k]:
        ingredients = c["ingredients"]
        missing = _compute_missing_ingredients(ingredients, pantry_item_names)

        results.append(
            {
                "id": c["id"],
                "title": c["title"],
                "time_minutes": c["time_minutes"],
                "diet": c["diet"],
                "missing_ingredients": missing,
                "cuisine": c["cuisine"],
                "avg_rating": c["avg_rating"],
                # internal scores still intentionally hidden
            }
        )

    return results
