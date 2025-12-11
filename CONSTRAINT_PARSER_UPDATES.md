# Constraint Parser Enhancements

## Overview
The natural language constraint parser in `/backend/routers/chat.py` has been significantly enhanced to support more sophisticated user queries and configurable filtering options.

## New Features

### 1. Configurable Expiring Window
Users can now specify how soon items should expire when asking for recipes:
- **Syntax**: "expiring in N days" (e.g., "expiring in 2 days")
- **Default**: 3 days if not specified
- **Examples**:
  - "What can I make with expiring in 1 day?" → Uses 1-day window
  - "Use items expiring soon" → Uses default 3-day window
  - "Recipes using expiring in 5 days" → Uses 5-day window

**Implementation**: 
- Regex pattern: `r"expiring\s+in\s+(\d+)\s+days?"`
- Stored in `constraints._expiring_window_days` 
- Used by `score_recipes()` to determine which pantry items are "expiring soon"

### 2. Additional Diet Type Support
Extended diet keyword detection:
- **Existing**: vegan, vegetarian, pescatarian
- **New**: keto, ketogenic
- **Gluten-free**: Special handling that adds gluten, wheat, and bread to exclude_ingredients

**Examples**:
- "keto recipe" → diet_types = ["keto"]
- "ketogenic meal" → diet_types = ["keto"]
- "gluten-free pasta" → exclude_ingredients includes ["gluten", "wheat", "bread"]

### 3. Improved Include/Exclude Ingredient Parsing
Enhanced natural language support for ingredient preferences:

#### Include Patterns
Captures ingredients user wants to include with multiple natural phrasings:
- "use X", "include X", "want X", "need X"
- "make with X", "recipe with X", "something with X"
- "what can I make with X"

**Multi-item support**: "make with chicken and fish" → includes both
**Examples**:
- "I want to use chicken" → include_ingredients = ["chicken"]
- "make something with chicken and fish" → include_ingredients = ["chicken", "fish"]
- "what can I make with beef and rice?" → include_ingredients = ["beef", "rice"]

#### Exclude Patterns
Captures ingredients user wants to avoid with multiple natural phrasings:
- "no X", "don't use X", "exclude X", "without X"
- "allergic to X", "can't have X", "cannot have X"
- "dislike X"

**Multi-item support**: "allergic to peanuts and shellfish" → excludes both
**Examples**:
- "no dairy" → exclude_ingredients = ["dairy"]
- "allergic to peanuts and shellfish" → exclude_ingredients = ["peanuts", "shellfish"]
- "no gluten, exclude dairy" → exclude_ingredients includes both
- "can't have nuts and tree nuts" → exclude_ingredients includes both

**Smart boundary detection**: Multiple exclude phrases like "no dairy and no nuts" correctly captures both items

### 4. Deduplication
Include and exclude lists are automatically deduplicated to remove redundant entries.

## Implementation Details

### Function: `parse_constraints_from_message(message: str) -> UserConstraints`

**Processing Order**:
1. Time constraints (quick, fast, under 30, etc.)
2. Diet constraints (vegan, vegetarian, pescatarian, keto, gluten-free)
3. Protein constraint detection
4. Light/healthy constraint
5. Carb constraints (high carb, low carb)
6. **NEW**: Expiring window parsing with configurable days
7. **NEW**: Improved include/exclude regex patterns
8. **NEW**: Deduplication of ingredient lists

**Regex Patterns Used**:
- **Expiring window**: `r"expiring\s+in\s+(\d+)\s+days?"`
- **Include phrases**: 
  - `r"(?:use|include|want|need)\s+([a-z0-9,\s&\-]+?)(?:\s+(?:and|or|please|recipe|to make)|\?|$)"`
  - `r"(?:make with|recipe with|something with|what\s+can\s+i\s+make\s+with)\s+([a-z0-9,\s&\-]+?)(?:\s+(?:and|or|please|no|don't|exclude|without|allergic|dislike)|\?|$)"`
- **Exclude phrases**:
  - `r"(?:no|don't use|dont use|can't have|cannot have|allergic to|dislike|exclude|without)\s+([a-z0-9,\s&\-]+?)(?=,|and\s+(?:no|don't|allergic|exclude|dislike|without)|make|recipe|with|use|\?|$)"`

**Storage**:
- `constraints._expiring_window_days` (integer, default 3)
- `constraints.include_ingredients` (list of strings)
- `constraints.exclude_ingredients` (list of strings)
- `constraints.diet_types` (list of strings)
- `constraints.prioritize_ingredient` ("protein", "expiring", or None)
- `constraints.prioritize_macro` ("high_carb", "low_carb", or None)

### Function: `score_recipes(...) -> List[dict]`

**Updated to use configurable expiring window**:
```python
expiring_soon_days = getattr(constraints, "_expiring_window_days", 3)
```

This allows the scoring function to dynamically adjust which items are considered "expiring soon" based on user input.

## Example User Conversations

### Example 1: Allergy-Aware Cooking
```
User: "I'm allergic to peanuts and shellfish. Make something with chicken that expires in 1 day."
Parsed:
  - exclude_ingredients: ["peanuts", "shellfish"]
  - include_ingredients: ["chicken"]
  - prioritize_ingredient: "expiring"
  - _expiring_window_days: 1
```

### Example 2: Keto Diet
```
User: "Keto recipe, no dairy, quick preparation"
Parsed:
  - diet_types: ["keto"]
  - exclude_ingredients: ["dairy"]
  - max_time_minutes: 20
```

### Example 3: Gluten-Free & Vegetarian
```
User: "Gluten-free vegetarian pasta, high protein"
Parsed:
  - diet_types: ["vegetarian"]
  - exclude_ingredients: ["gluten", "wheat", "bread"]
  - include_ingredients: ["protein", "chicken", "fish", ...]
  - prioritize_ingredient: "protein"
```

## Testing

All features have been tested with:
- Configurable expiring windows (1, 2, 3, 5 days)
- Multiple diet types (keto, gluten-free, pescatarian, etc.)
- Natural language include/exclude phrases
- Multi-item allergies/preferences ("allergic to X and Y")
- Deduplicated ingredient lists
- Combined constraints in single messages

## Files Modified

- `/backend/routers/chat.py`
  - Enhanced `parse_constraints_from_message()` function
  - Updated `score_recipes()` to use `_expiring_window_days`

## Backward Compatibility

All changes are backward compatible:
- Existing simple keywords still work
- Default expiring window remains 3 days
- All constraint parsing is additive (no removed features)
- Constraints with unset fields default to None or empty lists
