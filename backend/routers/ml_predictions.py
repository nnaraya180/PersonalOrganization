"""
backend/routers/ml_predictions.py
FastAPI router for mood and energy predictions from nutrition data.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ml.mood_energy_model import predict_both
from ml.nutrition_import import parse_recipe_nutrition, NutritionData

router = APIRouter(prefix="/api/ml", tags=["ml-predictions"])


class NutritionInput(BaseModel):
    """Direct nutrition input model."""
    calories: Optional[float] = None
    protein: Optional[float] = None
    protein_g: Optional[float] = None
    carbs: Optional[float] = None
    carbs_g: Optional[float] = None
    fat: Optional[float] = None
    fat_g: Optional[float] = None
    sugar: Optional[float] = None
    sugar_g: Optional[float] = None
    fiber: Optional[float] = None
    fiber_g: Optional[float] = None


class PredictMoodEnergyRequest(BaseModel):
    """Request model for mood/energy prediction."""
    nutrition: Optional[Dict[str, Any]] = None
    recipe_api_data: Optional[Dict[str, Any]] = None
    source: Optional[str] = "generic"  # 'spoonacular', 'edamam', 'usda', 'generic'


class PredictMoodEnergyResponse(BaseModel):
    """Response model for mood/energy prediction."""
    mood: Dict[str, Any]
    energy: Dict[str, Any]


class ImportRecipeRequest(BaseModel):
    """Request model for recipe import with nutrition extraction."""
    source: str = "generic"
    recipe_data: Dict[str, Any]


class ImportRecipeResponse(BaseModel):
    """Response model for recipe import."""
    nutrition: Dict[str, Optional[float]]
    completeness: float
    missing_fields: List[str]
    predictions: Dict[str, Any]


@router.post("/predict-mood-energy", response_model=PredictMoodEnergyResponse)
async def predict_mood_energy(request: PredictMoodEnergyRequest):
    """
    Endpoint to predict mood and energy from recipe nutrition.
    Accepts various formats of nutrition data.
    
    Example requests:
    
    1. Direct nutrition data:
    ```json
    {
        "nutrition": {
            "calories": 450,
            "protein_g": 25,
            "carbs_g": 50,
            "fat_g": 15
        }
    }
    ```
    
    2. Recipe from external API:
    ```json
    {
        "source": "spoonacular",
        "recipe_api_data": { ... }
    }
    ```
    
    3. Partial data (will estimate missing values):
    ```json
    {
        "nutrition": {
            "calories": 450
        }
    }
    ```
    """
    nutrition_dict = None
    
    # Option 1: Direct nutrition data
    if request.nutrition:
        nutrition_dict = request.nutrition
    
    # Option 2: Recipe from external API
    elif request.recipe_api_data:
        source = request.source or "generic"
        nutrition_obj = parse_recipe_nutrition(source, request.recipe_api_data)
        nutrition_dict = nutrition_obj.to_dict()
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'nutrition' or 'recipe_api_data'"
        )
    
    # Normalize field names (handle both 'protein' and 'protein_g' formats)
    normalized = {}
    for key, value in nutrition_dict.items():
        if value is not None:
            # Map common variations to our standard format
            if key in ['protein', 'protein_g']:
                normalized['protein_g'] = value
            elif key in ['carbs', 'carbs_g', 'carbohydrates']:
                normalized['carbs_g'] = value
            elif key in ['fat', 'fat_g', 'total_fat']:
                normalized['fat_g'] = value
            elif key in ['sugar', 'sugar_g', 'sugars']:
                normalized['sugar_g'] = value
            elif key in ['fiber', 'fiber_g']:
                normalized['fiber_g'] = value
            elif key == 'calories':
                normalized['calories'] = value
    
    # Make prediction
    mood_result, energy_result = predict_both(normalized)
    
    if mood_result is None or energy_result is None:
        raise HTTPException(
            status_code=400,
            detail='Insufficient nutrition data for prediction. At minimum, provide calories.'
        )
    
    return PredictMoodEnergyResponse(
        mood=mood_result,
        energy=energy_result
    )


@router.post("/import-recipe", response_model=ImportRecipeResponse)
async def import_recipe(request: ImportRecipeRequest):
    """
    Import recipe from external source and extract nutrition.
    Returns nutrition data, completeness metrics, and mood/energy predictions.
    
    Example request:
    ```json
    {
        "source": "generic",
        "recipe_data": {
            "name": "Chicken Salad",
            "calories": 350,
            "protein": 28,
            "carbs": 12,
            "fat": 22
        }
    }
    ```
    """
    source = request.source
    recipe_data = request.recipe_data
    
    # Parse nutrition from the recipe data
    nutrition_obj = parse_recipe_nutrition(source, recipe_data)
    
    # Get predictions
    nutrition_dict = nutrition_obj.to_dict()
    mood_result, energy_result = predict_both(nutrition_dict)
    
    if mood_result is None or energy_result is None:
        raise HTTPException(
            status_code=400,
            detail='Unable to make predictions from provided data'
        )
    
    return ImportRecipeResponse(
        nutrition=nutrition_dict,
        completeness=nutrition_obj.get_completeness(),
        missing_fields=nutrition_obj.get_missing_fields(),
        predictions={
            'mood': mood_result,
            'energy': energy_result
        }
    )


@router.get("/health")
async def health_check():
    """Health check endpoint to verify ML models are loaded."""
    try:
        # Test with minimal data
        test_data = {'calories': 400}
        mood, energy = predict_both(test_data)
        
        if mood and energy:
            return {
                "status": "healthy",
                "models_loaded": True,
                "message": "ML prediction service is operational"
            }
        else:
            return {
                "status": "degraded",
                "models_loaded": False,
                "message": "Models loaded but prediction failed"
            }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"ML service unavailable: {str(e)}"
        )
