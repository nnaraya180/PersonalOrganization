from fastapi import FastAPI, Depends, APIRouter
from typing import List, Optional
from sqlmodel import select, Session
from database import init_db, get_session
from datetime import date
from models import (
    Item,
    ItemCreate,
    Recipe,
    RecipeIngredient,
    UserConstraints,
    UserProfile,
)
from recommender import recommend_recipes_mvp
from routers.chat import router as chat_router

from pydantic import BaseModel 
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from openai import OpenAI
from dotenv import load_dotenv

from recommender import recommend_recipes_mvp
from routers.chat import router as chat_router
from routers.ml_predictions import router as ml_router

load_dotenv()  # loads LITELLM_TOKEN from .env if you use one

class RecipeCreate(BaseModel):
    title: str
    ingredients: List[str]  # free text lines like "2 eggs", "olive oil"

    # Optional metadata fields to populate DB columns
    time_minutes: Optional[int] = None
    diet: Optional[str] = None
    cuisine: Optional[str] = None
    avg_rating: Optional[float] = None

    # Nutrition estimates
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    calories: Optional[int] = None

class RecipeOut(BaseModel):
    id: int
    title: str
    time_minutes: Optional[int] = None
    diet: Optional[str] = None
    cuisine: Optional[str] = None
    avg_rating: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    calories: Optional[int] = None
    ingredients: List[str]

class ItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    quantity: int | None = None
    # Optional dates
    purchase_date: Optional[date] = None
    expiration_date: Optional[date] = None

    # Optional estimated macros
    estimated_calories: Optional[float] = None
    estimated_protein_g: Optional[float] = None
    estimated_carbs_g: Optional[float] = None
    estimated_fat_g: Optional[float] = None

class ConsumePayload(BaseModel):
    amount: int

class RestockPayload(BaseModel):
    amount: int

class RecommendedRecipe(BaseModel):
    id: int
    title: str
    mood: Optional[str] = None   # to be filled later by ML
    time_minutes: Optional[int] = None
    diet: Optional[str] = None
    ingredients: List[str]


class RecommendationRequest(BaseModel):
    mood: Optional[str] = None
    time_limit: Optional[str] = None   # "<20", "20-40", ">40"
    diet: Optional[str] = None
    pantry_items: List[str] = []


class RecommendationResponse(BaseModel):
    recipes: List[RecommendedRecipe]



app = FastAPI()
router = APIRouter()

# ---- Duke LITELLM client setup ----
api_key = os.getenv("LITELLM_TOKEN")
if not api_key:
    raise RuntimeError("LITELLM_TOKEN not found. Set it in the environment.")

client = OpenAI(
    api_key=api_key,
    base_url="https://litellm.oit.duke.edu/v1",
)
# -----------------------------------

# Configure CORS - allow our known frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://kitchen-pal-r773.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chat router (provides /chat/what_can_i_make and /chat/log)
app.include_router(chat_router)

# Include ML predictions router (provides /api/ml/predict-mood-energy and /api/ml/import-recipe)
app.include_router(ml_router)


@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.get("/items", response_model=List[Item])
def list_items(session: Session = Depends(get_session)):
    # Build a SELECT query for all rows in the Item table
    statement = select(Item)
    results = session.exec(statement)
    items = results.all()
    return items

@app.post("/items", response_model=Item)
def create_item(payload: ItemCreate, session: Session = Depends(get_session)):
    data = payload.dict()
    # Default purchase_date to today if not provided
    if data.get("purchase_date") is None:
        data["purchase_date"] = date.today()
    item = Item(**data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.post("/items/bulk", response_model=List[Item])
def create_items_bulk(payload: List[ItemCreate], session: Session = Depends(get_session)):
    items = []
    for p in payload:
        d = p.dict()
        if d.get("purchase_date") is None:
            d["purchase_date"] = date.today()
        items.append(Item(**d))
    session.add_all(items)
    session.commit()
    # refresh to get IDs; small loop is fine for now
    for it in items:
        session.refresh(it)
    return items

@app.post("/recipes/seed", summary="Insert a few sample recipes for testing")
def seed_recipes(session: Session = Depends(get_session)):
    # If already seeded, no-op
    existing = session.exec(select(Recipe)).first()
    if existing:
        return {"status": "already seeded"}

    # Define 4 minimal recipes
    data = [
        {
            "title": "Spinach Omelette",
            "ingredients": ["eggs", "spinach", "olive oil", "salt", "black pepper"]
        },
        {
            "title": "Garlic Butter Salmon",
            "ingredients": ["salmon", "garlic", "butter", "lemon", "salt", "black pepper"]
        },
        {
            "title": "Simple Pasta with Tomato Sauce",
            "ingredients": ["dried pasta", "olive oil", "garlic", "pasta sauce", "salt"]
        },
        {
            "title": "Fried Rice (Pantry Style)",
            "ingredients": ["rice", "eggs", "soy sauce", "vegetable oil", "frozen peas and carrots"]
        },
    ]

    # Insert
    for r in data:
        recipe = Recipe(title=r["title"])
        session.add(recipe)
        session.flush()  # get recipe.id
        for ing in r["ingredients"]:
            session.add(RecipeIngredient(recipe_id=recipe.id, name=ing.lower()))
    session.commit()
    return {"status": "seeded", "count": len(data)}


@app.get("/recipes/match", summary="Return recipes ranked by pantry coverage")
def match_recipes(min_coverage: float = 0.3, session: Session = Depends(get_session)):
    # 1) Canonical pantry tokens
    pantry_names = {canonicalize(i.name) for i in session.exec(select(Item)).all()}

    # 2) Load recipes/ingredients → canonicalize
    recipes = session.exec(select(Recipe)).all()
    out = []

    for r in recipes:
        ing_rows = session.exec(select(RecipeIngredient).where(RecipeIngredient.recipe_id == r.id)).all()
        rec_ing = [canonicalize(x.name) for x in ing_rows if x.name]
        if not rec_ing:
            continue

        have = [ing for ing in rec_ing if ing in pantry_names]
        missing = [ing for ing in rec_ing if ing not in pantry_names]

        coverage = len(have) / len(rec_ing)
        if coverage >= min_coverage:
            out.append({
                "recipe_id": r.id,
                "title": r.title,
                "coverage": round(coverage, 2),
                "have": have,
                "missing": missing
            })

    out.sort(key=lambda x: (-x["coverage"], len(x["missing"]), x["title"]))
    return {"results": out}

@app.post("/recipes/add", summary="Create a recipe from title + ingredient lines")
def create_recipe(payload: RecipeCreate, session: Session = Depends(get_session)):
    recipe = Recipe(
        title=payload.title,
        time_minutes=payload.time_minutes,
        diet=payload.diet,
        # optional fields
        cuisine=payload.cuisine,
        avg_rating=payload.avg_rating,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        calories=payload.calories,
    )
    session.add(recipe)
    session.flush()  # get recipe.id

    # store each ingredient as a row; keep using the canonicalizer
    for line in payload.ingredients:
        line = (line or "").strip()
        if not line:
            continue
        session.add(RecipeIngredient(recipe_id=recipe.id, name=canonicalize(line)))

    session.commit()

    # return the created recipe with its (canonical) ingredients
    ing_rows = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    ).all()
    return {
        "recipe_id": recipe.id,
        "title": recipe.title,
        "ingredients": [r.name for r in ing_rows],
    }

@app.post("/recipes/bulk", summary="Create multiple recipes in one call")
def create_recipes_bulk(payload: List[RecipeCreate], session: Session = Depends(get_session)):
    created = []
    for r in payload:
        recipe = Recipe(
            title=r.title,
            time_minutes=r.time_minutes,
            diet=r.diet,
            cuisine=r.cuisine,
            avg_rating=r.avg_rating,
            protein_g=r.protein_g,
            carbs_g=r.carbs_g,
            fat_g=r.fat_g,
            calories=r.calories,
        )
        session.add(recipe)
        session.flush()
        for line in r.ingredients:
            line = (line or "").strip()
            if not line:
                continue
            session.add(RecipeIngredient(recipe_id=recipe.id, name=canonicalize(line)))
        created.append(recipe.id)

    session.commit()
    return {"status": "created", "count": len(created), "recipe_ids": created}

@app.post("/recipes/backfill_metadata", summary="Fill time_minutes and diet for existing recipes")
def backfill_recipe_metadata(session: Session = Depends(get_session)):
    recipes = session.exec(select(Recipe)).all()
    """
    One-time helper to populate time_minutes and diet for recipes
    that already exist in the database. Safe to call multiple times.
    """

    # Map from recipe title -> metadata
    title_meta = {
        "Spinach Omelette": {
            "time_minutes": 10,
            "diet": "vegetarian",
        },
        "Garlic Butter Salmon": {
            "time_minutes": 20,
            "diet": "pescatarian",
        },
        "Simple Pasta with Tomato Sauce": {
            "time_minutes": 20,
            "diet": "vegetarian",
        },
        "Fried Rice (Pantry Style)": {
            "time_minutes": 25,
            "diet": "vegetarian",
        },
        "Yogurt & Dates Bowl": {
            "time_minutes": 5,
            "diet": "vegetarian",
        },
        "Simple Tuna Pasta": {
            "time_minutes": 20,
            "diet": "pescatarian",
        },
        "Stir-Fried Greens": {
            "time_minutes": 10,
            "diet": "vegan",
        },
    }

    recipes = session.exec(select(Recipe)).all()
    updated = 0

    for r in recipes:
        meta = title_meta.get(r.title)
        if not meta:
            # Unknown title, skip
            continue

        changed = False

        if r.time_minutes is None:
            r.time_minutes = meta["time_minutes"]
            changed = True

        if r.diet is None:
            r.diet = meta["diet"]
            changed = True

        if changed:
            session.add(r)
            updated += 1

    session.commit()
    return {"status": "ok", "updated": updated}


@app.get("/recipes", response_model=List[RecipeOut], summary="List all recipes with ingredients")
def list_recipes(session: Session = Depends(get_session)):
    recipes = session.exec(select(Recipe)).all()
    out: List[RecipeOut] = []
    for r in recipes:
        ing_rows = session.exec(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == r.id)
        ).all()
        out.append(RecipeOut(
            id=r.id,
            title=r.title,
            time_minutes=r.time_minutes,
            diet=r.diet,
            cuisine=getattr(r, "cuisine", None),
            avg_rating=getattr(r, "avg_rating", None),
            protein_g=getattr(r, "protein_g", None),
            carbs_g=getattr(r, "carbs_g", None),
            fat_g=getattr(r, "fat_g", None),
            calories=getattr(r, "calories", None),
            ingredients=[x.name for x in ing_rows],
        ))
    return out


@app.get("/recipes/{recipe_id}", response_model=RecipeOut, summary="Get one recipe by id")
def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    r = session.get(Recipe, recipe_id)
    if not r:
        return {"detail": "Not found"}
    ing_rows = session.exec(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == r.id)
    ).all()
    return RecipeOut(
        id=r.id,
        title=r.title,
        time_minutes=r.time_minutes,
        diet=r.diet,
        cuisine=getattr(r, "cuisine", None),
        avg_rating=getattr(r, "avg_rating", None),
        protein_g=getattr(r, "protein_g", None),
        carbs_g=getattr(r, "carbs_g", None),
        fat_g=getattr(r, "fat_g", None),
        calories=getattr(r, "calories", None),
        ingredients=[x.name for x in ing_rows],
    )

@app.patch("/items/{item_id}", response_model=Item, summary="Update some fields of an item")
def update_item(item_id: int, payload: ItemUpdate, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        return {"detail": "Not found"}
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.delete("/items/{item_id}", summary="Delete an item")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        return {"detail": "Not found"}
    session.delete(item)
    session.commit()
    return {"status": "deleted", "id": item_id}

@app.post("/items/{item_id}/consume", response_model=Item, summary="Decrease quantity by amount (not below 0)")
def consume_item(item_id: int, payload: ConsumePayload, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        return {"detail": "Not found"}
    amt = max(0, int(payload.amount or 0))
    item.quantity = max(0, (item.quantity or 0) - amt)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.post("/items/{item_id}/restock", response_model=Item, summary="Increase quantity by amount")
def restock_item(item_id: int, payload: RestockPayload, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        return {"detail": "Not found"}
    amt = max(0, int(payload.amount or 0))
    item.quantity = (item.quantity or 0) + amt
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@app.post("/recommend")
def recommend_recipes_endpoint(
    constraints: UserConstraints,          # parsed from JSON body
    session: Session = Depends(get_session),
):
    """
    Recommend recipes based on:
    - all items in the house (Item table)
    - constraints selected by the user (cuisine, mood, etc.)
    """

    # 1) Load ALL recipes from the DB
    recipes = session.exec(select(Recipe)).all()

    # 2) Adapt Recipe + RecipeIngredient objects into simple dicts
    #    so the recommender sees a consistent shape.
    recipe_payloads = []
    for recipe in recipes:
        ingredient_names = [ri.name for ri in recipe.ingredients]

        recipe_payloads.append(
            {
                "id": recipe.id,
                "title": recipe.title,
                "ingredients": ingredient_names,
                "time_minutes": recipe.time_minutes,
                "diet": recipe.diet,
                # If you don't have these columns yet, they'll just be None.
                "cuisine": getattr(recipe, "cuisine", None),
                "avg_rating": getattr(recipe, "avg_rating", None),
         }
    )

    # 3) Load ALL items (pantry + fridge + freezer + anything else)
    items = session.exec(select(Item)).all()
    pantry_names = [item.name for item in items]

    # 4) Simple single-user profile for MVP
    user_profile = UserProfile(
        allergies=[],      # later: pull from user settings
        diet_types=[],     # e.g. ["vegetarian"]
    )

    # 5) Call your recommender
    recommendations = recommend_recipes_mvp(
        recipes=recipe_payloads,
        pantry_item_names=pantry_names,
        constraints=constraints,
        user_profile=user_profile,
        top_k=5,
    )

    # 6) Return user-facing recommendations
    return recommendations


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        completion = client.chat.completions.create(
            model="GPT 4.1 Mini",  # or the exact model string your TA used
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant inside a pantry and recipe app. "
                        "Answer in a friendly, concise way. Help the user with meal ideas, "
                        "recipes, pantry planning, leftovers, and cooking tips."
                    ),
                },
                {"role": "user", "content": request.message},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        reply = completion.choices[0].message.content
        return ChatResponse(reply=reply)
    except Exception as e:
        print("Chat error:", e)
        raise HTTPException(status_code=500, detail="LLM error via Duke gateway")


# --- Normalization + strict synonyms ---

import re

# harmless descriptors we can drop without changing meaning
STORAGE_DESCRIPTORS = {
    "frozen", "fresh", "loose", "leaf", "bottle", "spice", "spice bottle",
}

def normalize_safe(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[’`]", "'", s)                  # normalize apostrophes
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)        # keep letters/digits/space/hyphen/apo
    s = re.sub(r"\s+", " ", s).strip()

    # drop storage/descriptive words when they’re standalone
    words = [w for w in s.split() if w not in STORAGE_DESCRIPTORS]
    s = " ".join(words)

    # light plural → singular (cheap and conservative)
    if s.endswith("es") and len(s) > 3:
        s = s[:-2]
    elif s.endswith("s") and len(s) > 2 and not s.endswith("ss"):
        s = s[:-1]

    return s

# Only add TRUE synonyms here (no brand→generic, no greek yogurt→yogurt)
SYNONYMS = {
    "scallion": "green onion",
    "green onions": "green onion",
    "garbanzo bean": "chickpea",
    "garbanzo": "chickpea",
    "chickpeas": "chickpea",
    # add more ONLY if truly equivalent
}

def canonicalize(token: str) -> str:
    t = normalize_safe(token)
    return SYNONYMS.get(t, t)
