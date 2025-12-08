from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from typing import List
from pydantic import BaseModel
from datetime import date

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str | None = None
    quantity: int | None = 0


class ItemCreate(SQLModel):
    name: str
    category: str = "pantry"   # default so you can skip it
    quantity: int = 1          # default so you can skip it

    
# --- Minimal recipe models (string-based ingredients for speed) ---
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str

    # NEW columns you added
    time_minutes: int | None = Field(default=None, index=True)
    diet: str | None = Field(default=None, index=True)

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
    expiration_date: Optional[date] = None


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
    

class UserProfile(BaseModel):
    """
    Simplified for single-user MVP.
    No user_id, no likes/dislikes/history yet.
    """
    allergies: List[str] = []    # ["peanuts", "shellfish"]
    diet_types: List[str] = []   # ["vegetarian", "vegan"]
