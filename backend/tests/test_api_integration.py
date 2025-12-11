"""
Integration tests for /chat/recipes endpoint.
Tests the full API flow including filters, scoring, and response structure.
"""
import pytest
import sys
sys.path.insert(0, '/Users/neilnarayanan/code/personal-assistant/backend')

from fastapi.testclient import TestClient
from main import app
from database import get_session, init_db
from models import Recipe, RecipeIngredient, Item
from sqlmodel import Session, create_engine, SQLModel
from datetime import date, timedelta


# Create test database in memory
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)


def get_test_session():
    """Override session for testing."""
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_session] = get_test_session
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Create fresh test database for each test."""
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


def seed_test_data(session: Session):
    """Helper to seed test recipes and pantry items."""
    today = date.today()
    
    # Add pantry items
    items = [
        Item(name="chicken", category="protein", quantity=2, 
             expiration_date=today + timedelta(days=2)),
        Item(name="rice", category="grain", quantity=5),
        Item(name="spinach", category="vegetable", quantity=1,
             expiration_date=today + timedelta(days=3)),
        Item(name="eggs", category="protein", quantity=12,
             expiration_date=today + timedelta(days=7)),
        Item(name="cheese", category="dairy", quantity=1),
    ]
    for item in items:
        session.add(item)
    
    # Add recipes
    recipe1 = Recipe(
        title="High Protein Bowl",
        time_minutes=20,
        diet="pescatarian",
        protein_g=38,
        carbs_g=45,
        fat_g=12,
        calories=550
    )
    session.add(recipe1)
    session.flush()
    
    for ing in ["chicken", "rice", "spinach"]:
        session.add(RecipeIngredient(recipe_id=recipe1.id, name=ing))
    
    recipe2 = Recipe(
        title="Quick Omelette",
        time_minutes=10,
        diet="vegetarian",
        protein_g=18,
        carbs_g=5,
        fat_g=15,
        calories=280
    )
    session.add(recipe2)
    session.flush()
    
    for ing in ["eggs", "cheese", "spinach"]:
        session.add(RecipeIngredient(recipe_id=recipe2.id, name=ing))
    
    recipe3 = Recipe(
        title="Heavy Pasta",
        time_minutes=45,
        diet="vegetarian",
        protein_g=12,
        carbs_g=85,
        fat_g=25,
        calories=780
    )
    session.add(recipe3)
    session.flush()
    
    for ing in ["pasta", "cream", "cheese"]:
        session.add(RecipeIngredient(recipe_id=recipe3.id, name=ing))
    
    session.commit()


class TestChatRecipesEndpoint:
    """Integration tests for /chat/recipes endpoint."""
    
    def test_basic_request_returns_recipes(self):
        """Basic request should return recipe suggestions."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "mood": "focus",
            "energy": "high"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "recipes" in data
        assert isinstance(data["recipes"], list)
        assert len(data["recipes"]) > 0
    
    def test_nutrition_goal_high_protein(self):
        """Request with high_protein goal should prioritize high protein recipes."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "high_protein",
            "energy": "high"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return recipes, top one should have explanation/debug
        assert len(data["recipes"]) > 0
        top_recipe = data["recipes"][0]
        
        assert "explanation" in top_recipe
        assert "debug" in top_recipe
        assert "nutrition" in top_recipe["debug"]
        assert "goal" in top_recipe["debug"]["nutrition"]
        assert top_recipe["debug"]["nutrition"]["goal"] == "high_protein"
        
        # High protein bowl should rank first
        assert "protein" in top_recipe["title"].lower() or top_recipe["debug"]["nutrition"]["score"] > 0
    
    def test_low_carb_goal(self):
        """Request with low_carb goal should prioritize low carb recipes."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "low_carb"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        top_recipe = data["recipes"][0]
        assert "Omelette" in top_recipe["title"], "Omelette (low carb) should rank higher than pasta"
    
    def test_time_filter(self):
        """Request with max_time should filter out long recipes."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "max_time_minutes": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Heavy Pasta (45 min) should be filtered out
        titles = [r["title"] for r in data["recipes"]]
        assert "Heavy Pasta" not in titles
        assert len(data["recipes"]) >= 2
    
    def test_exclude_ingredients(self):
        """Request excluding ingredients should filter recipes."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "exclude_ingredients": ["cheese"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Only High Protein Bowl should remain (no cheese)
        assert len(data["recipes"]) == 1
        assert "Bowl" in data["recipes"][0]["title"]
    
    def test_include_ingredients(self):
        """Request with include_ingredients should require them."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "include_ingredients": ["chicken"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Only High Protein Bowl has chicken
        assert len(data["recipes"]) == 1
        assert "Bowl" in data["recipes"][0]["title"]
    
    def test_expiring_items_scored(self):
        """Recipes using expiring items should have expiring score > 0."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "mood": "neutral"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Find recipe with expiring ingredients (chicken, spinach expire soon)
        for recipe in data["recipes"]:
            if "Bowl" in recipe["title"] or "Omelette" in recipe["title"]:
                assert recipe["debug"]["expiring"]["score"] > 0
                assert len(recipe["debug"]["expiring"]["matched"]) > 0
    
    def test_explanation_present(self):
        """All returned recipes should have explanation field."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "high_protein",
            "mood": "focus"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        for recipe in data["recipes"]:
            assert "explanation" in recipe
            assert isinstance(recipe["explanation"], str)
            assert len(recipe["explanation"]) > 0
    
    def test_debug_structure(self):
        """Debug field should contain all expected components."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "high_protein",
            "energy": "high"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        top_recipe = data["recipes"][0]
        debug = top_recipe["debug"]
        
        # Check structure
        assert "weights" in debug
        assert "coverage" in debug
        assert "expiring" in debug
        assert "nutrition" in debug
        assert "mood_energy" in debug
        
        # Check nutrition debug details
        nutrition_debug = debug["nutrition"]
        assert "score" in nutrition_debug
        assert "explanation" in nutrition_debug
        assert "goal" in nutrition_debug
        assert "macros" in nutrition_debug
        assert "components" in nutrition_debug
    
    def test_empty_pantry_returns_message(self):
        """Empty pantry should return helpful message."""
        # Don't seed any data
        response = client.post("/chat/recipes", json={
            "mood": "focus"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "empty" in data["reply"].lower() or "no recipes" in data["reply"].lower()
    
    def test_no_matching_recipes(self):
        """Impossible constraints should return helpful message."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "include_ingredients": ["lobster", "caviar"],  # Not in pantry
            "max_time_minutes": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "couldn't find" in data["reply"].lower() or "no recipes" in data["reply"].lower()
    
    def test_nutrition_goal_in_reply(self):
        """Reply should mention the nutrition goal when specified."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "high_protein"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "high protein" in data["reply"].lower()
    
    def test_multiple_filters_combined(self):
        """Multiple filters should work together correctly."""
        with Session(test_engine) as session:
            seed_test_data(session)
        
        response = client.post("/chat/recipes", json={
            "nutrition_goal": "low_carb",
            "max_time_minutes": 25,
            "exclude_ingredients": ["cream"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should get Quick Omelette (low carb, quick, no cream)
        # Should filter out Heavy Pasta (high carb, has cream)
        titles = [r["title"] for r in data["recipes"]]
        assert "Omelette" in str(titles)
        assert "Heavy Pasta" not in titles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
