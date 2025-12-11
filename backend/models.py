from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from typing import List
from pydantic import BaseModel
from datetime import date
from datetime import datetime

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str | None = None
    quantity: int | None = 0

    # Optional dates
    purchase_date: date | None = None
    expiration_date: date | None = None

    # Estimated macros per item (optional)
    estimated_calories: float | None = None
    estimated_protein_g: float | None = None
    estimated_carbs_g: float | None = None
    estimated_fat_g: float | None = None


class ItemCreate(SQLModel):
    name: str
    category: str = "pantry"   # default so you can skip it
    quantity: int = 1          # default so you can skip it

    # Optional dates (ISO 8601 strings via Pydantic)
    purchase_date: date | None = None
    expiration_date: date | None = None

    # Optional estimated macros
    estimated_calories: float | None = None
    estimated_protein_g: float | None = None
    estimated_carbs_g: float | None = None
    estimated_fat_g: float | None = None

    
# --- Minimal recipe models (string-based ingredients for speed) ---
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str

    # NEW columns you added
    time_minutes: int | None = Field(default=None, index=True)
    diet: str | None = Field(default=None, index=True)
    cuisine: str | None = Field(default=None, index=True)
    avg_rating: float | None = Field(default=None)
    
    # Nutrition fields (placeholder for later refinement)
    protein_g: float | None = Field(default=None)
    carbs_g: float | None = Field(default=None)
    fat_g: float | None = Field(default=None)
    calories: int | None = Field(default=None)

    # Optional expanded nutrition fields for richer scoring/labeling
    nutrition_protein_g: float | None = Field(default=None)
    nutrition_carbs_g: float | None = Field(default=None)
    nutrition_fat_g: float | None = Field(default=None)
    nutrition_calories: float | None = Field(default=None)
    nutrition_fiber_g: float | None = Field(default=None)
    nutrition_sugar_g: float | None = Field(default=None)
    nutrition_sodium_mg: float | None = Field(default=None)

    # 🔑 THIS is the missing relationship
    ingredients: List["RecipeIngredient"] = Relationship(back_populates="recipe")


class RecipeIngredient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id")
    name: str

    # Other side of the relationship
    recipe: Optional[Recipe] = Relationship(back_populates="ingredients")


class PantryItem(BaseModel):
    """
    Represents a single item in the user's pantry.
    Expiration is optional for now – we’ll use it later.
    """
    name: str                          # "chickpeas", "spinach"
    quantity: Optional[float] = None   # 1.0, 2.5, etc. (optional)
    unit: Optional[str] = None         # "can", "g", "cups", etc.
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None

    estimated_calories: Optional[float] = None
    estimated_protein_g: Optional[float] = None
    estimated_carbs_g: Optional[float] = None
    estimated_fat_g: Optional[float] = None


class UserConstraints(BaseModel):
    """
    Structured preferences extracted from the user's message.
    This is what the LLM will eventually fill in as JSON.
    """
    cuisine: Optional[List[str]] = None          # ["italian", "mexican"]
    mood: Optional[str] = None                   # "comfort", "light", "focus"
    energy_level: Optional[str] = None           # "low", "medium", "high"

    diet_types: Optional[List[str]] = None       # ["vegetarian", "gluten-free"]
    include_ingredients: Optional[List[str]] = None
    exclude_ingredients: Optional[List[str]] = None
    prioritize_ingredient: Optional[str] = None  # "chickpeas", "salmon"

    max_time_minutes: Optional[int] = None       # e.g. 30 for quick meals
    # Priority hints
    prioritize_ingredient: Optional[str] = None  # e.g. 'protein', 'expiring'
    prioritize_macro: Optional[str] = None       # e.g. 'high_carb', 'low_carb'
    nutrition_goal: Optional[str] = None         # e.g. 'high_protein', 'low_carb', 'low_calorie'
    

class UserProfile(BaseModel):
    """
    Simplified for single-user MVP.
    No user_id, no likes/dislikes/history yet.
    """
    allergies: List[str] = []    # ["peanuts", "shellfish"]
    diet_types: List[str] = []   # ["vegetarian", "vegan"]

class UserMealLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # For now we can hardcode / assume a single user (user_id = 1),
    # but keep this as a normal field so we can add auth later.
    user_id: Optional[int] = Field(default=None, index=True)

    # Link to a recipe if you have a Recipe model; optional so we can still log
    # feedback even if it wasn't from your internal recipe DB.
    recipe_id: Optional[int] = Field(default=None, index=True)
    recipe_title: str  # store the name for readability

    cooked_at: datetime = Field(default_factory=datetime.utcnow)

    # How much you liked it overall (1–5)
    taste_rating: Optional[int] = Field(default=None)

    # Simple taste tags captured as comma-separated strings, e.g. "spicy,fresh"
    liked_tags: Optional[str] = Field(default=None)
    disliked_tags: Optional[str] = Field(default=None)

    # How you felt after: "energized", "sluggish", "neutral", etc.
    feel_after: Optional[str] = Field(default=None)

    # Any free-form notes
    notes: Optional[str] = Field(default=None)

class UserTasteProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, unique=True)

    # Very simple boolean flags for now; you can expand later or switch to JSON.
    likes_spicy: bool = False
    likes_tangy: bool = False
    likes_creamy: bool = False
    likes_fresh_herbs: bool = False

    dislikes_heavy: bool = False
    dislikes_super_sweet: bool = False
