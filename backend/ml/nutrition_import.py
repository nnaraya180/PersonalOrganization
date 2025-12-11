"""
Helper for importing recipes from various sources and extracting nutrition data.
Handles multiple API formats and missing data scenarios.
"""
from typing import Dict, Optional, List
import requests
from dataclasses import dataclass

@dataclass
class NutritionData:
    """Standardized nutrition data structure."""
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    sugar_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Optional[float]]:
        """Convert to dict for ML model."""
        return {
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
            'sugar_g': self.sugar_g,
            'fiber_g': self.fiber_g
        }
    
    def get_completeness(self) -> float:
        """Return percentage of fields that are populated (0-1)."""
        fields = [self.calories, self.protein_g, self.carbs_g, 
                 self.fat_g, self.sugar_g, self.fiber_g]
        filled = sum(1 for f in fields if f is not None)
        return filled / len(fields)
    
    def get_missing_fields(self) -> List[str]:
        """Return list of field names that are None."""
        mapping = {
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
            'sugar_g': self.sugar_g,
            'fiber_g': self.fiber_g
        }
        return [name for name, value in mapping.items() if value is None]


class RecipeNutritionExtractor:
    """
    Extract nutrition data from various recipe sources and API formats.
    """
    
    @staticmethod
    def from_spoonacular(data: Dict) -> NutritionData:
        """
        Parse Spoonacular API response.
        Example: https://spoonacular.com/food-api/docs#Get-Recipe-Information
        """
        nutrition = NutritionData()
        
        if 'nutrition' in data:
            nutrients = data['nutrition'].get('nutrients', [])
            
            for nutrient in nutrients:
                name = nutrient.get('name', '').lower()
                amount = nutrient.get('amount')
                
                if 'calorie' in name:
                    nutrition.calories = amount
                elif 'protein' in name:
                    nutrition.protein_g = amount
                elif 'carbohydrate' in name:
                    nutrition.carbs_g = amount
                elif 'fat' in name and 'saturated' not in name:
                    nutrition.fat_g = amount
                elif 'sugar' in name:
                    nutrition.sugar_g = amount
                elif 'fiber' in name:
                    nutrition.fiber_g = amount
                elif 'sodium' in name:
                    nutrition.sodium_mg = amount
        
        return nutrition
    
    @staticmethod
    def from_edamam(data: Dict) -> NutritionData:
        """
        Parse Edamam API response.
        Example: https://developer.edamam.com/edamam-docs-recipe-api
        """
        nutrition = NutritionData()
        
        if 'totalNutrients' in data:
            nutrients = data['totalNutrients']
            
            # Edamam uses specific codes
            if 'ENERC_KCAL' in nutrients:
                nutrition.calories = nutrients['ENERC_KCAL'].get('quantity')
            if 'PROCNT' in nutrients:
                nutrition.protein_g = nutrients['PROCNT'].get('quantity')
            if 'CHOCDF' in nutrients:
                nutrition.carbs_g = nutrients['CHOCDF'].get('quantity')
            if 'FAT' in nutrients:
                nutrition.fat_g = nutrients['FAT'].get('quantity')
            if 'SUGAR' in nutrients:
                nutrition.sugar_g = nutrients['SUGAR'].get('quantity')
            if 'FIBTG' in nutrients:
                nutrition.fiber_g = nutrients['FIBTG'].get('quantity')
            if 'NA' in nutrients:
                nutrition.sodium_mg = nutrients['NA'].get('quantity')
        
        return nutrition
    
    @staticmethod
    def from_usda(data: Dict) -> NutritionData:
        """
        Parse USDA FoodData Central API response.
        Example: https://fdc.nal.usda.gov/api-guide.html
        """
        nutrition = NutritionData()
        
        if 'foodNutrients' in data:
            for nutrient in data['foodNutrients']:
                nutrient_name = nutrient.get('nutrient', {}).get('name', '').lower()
                amount = nutrient.get('amount')
                
                if 'energy' in nutrient_name:
                    nutrition.calories = amount
                elif 'protein' in nutrient_name:
                    nutrition.protein_g = amount
                elif 'carbohydrate' in nutrient_name and 'by difference' in nutrient_name:
                    nutrition.carbs_g = amount
                elif 'total lipid' in nutrient_name or 'fat' in nutrient_name:
                    nutrition.fat_g = amount
                elif 'sugars, total' in nutrient_name:
                    nutrition.sugar_g = amount
                elif 'fiber' in nutrient_name:
                    nutrition.fiber_g = amount
                elif 'sodium' in nutrient_name:
                    nutrition.sodium_mg = amount
        
        return nutrition
    
    @staticmethod
    def from_generic_json(data: Dict) -> NutritionData:
        """
        Parse generic JSON with common field names.
        Tries multiple common naming conventions.
        """
        nutrition = NutritionData()
        
        # Common field name variations
        calorie_fields = ['calories', 'energy', 'kcal', 'calorie']
        protein_fields = ['protein', 'protein_g', 'proteing', 'proteins']
        carb_fields = ['carbs', 'carbohydrates', 'carbs_g', 'carb', 'carbohydrate']
        fat_fields = ['fat', 'total_fat', 'fat_g', 'totalfat', 'fats']
        sugar_fields = ['sugar', 'sugars', 'sugar_g', 'total_sugar']
        fiber_fields = ['fiber', 'dietary_fiber', 'fiber_g', 'fibre']
        sodium_fields = ['sodium', 'sodium_mg', 'salt']
        
        # Try to find calories
        for field in calorie_fields:
            if field in data and data[field] is not None:
                nutrition.calories = float(data[field])
                break
        
        # Try to find protein
        for field in protein_fields:
            if field in data and data[field] is not None:
                nutrition.protein_g = float(data[field])
                break
        
        # Try to find carbs
        for field in carb_fields:
            if field in data and data[field] is not None:
                nutrition.carbs_g = float(data[field])
                break
        
        # Try to find fat
        for field in fat_fields:
            if field in data and data[field] is not None:
                nutrition.fat_g = float(data[field])
                break
        
        # Try to find sugar
        for field in sugar_fields:
            if field in data and data[field] is not None:
                nutrition.sugar_g = float(data[field])
                break
        
        # Try to find fiber
        for field in fiber_fields:
            if field in data and data[field] is not None:
                nutrition.fiber_g = float(data[field])
                break
        
        # Try to find sodium
        for field in sodium_fields:
            if field in data and data[field] is not None:
                nutrition.sodium_mg = float(data[field])
                break
        
        return nutrition
    
    @staticmethod
    def from_manual_input(calories=None, protein=None, carbs=None, 
                         fat=None, sugar=None, fiber=None) -> NutritionData:
        """Create nutrition data from manual input."""
        return NutritionData(
            calories=calories,
            protein_g=protein,
            carbs_g=carbs,
            fat_g=fat,
            sugar_g=sugar,
            fiber_g=fiber
        )


def parse_recipe_nutrition(source: str, data: Dict) -> NutritionData:
    """
    Main function to parse nutrition from any source.
    
    Args:
        source: One of 'spoonacular', 'edamam', 'usda', 'generic'
        data: The API response or data dict
    
    Returns:
        NutritionData object
    """
    extractor = RecipeNutritionExtractor()
    
    if source == 'spoonacular':
        return extractor.from_spoonacular(data)
    elif source == 'edamam':
        return extractor.from_edamam(data)
    elif source == 'usda':
        return extractor.from_usda(data)
    else:
        return extractor.from_generic_json(data)


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("TESTING NUTRITION EXTRACTION")
    print("=" * 60)
    
    # Example 1: Generic JSON (like from a recipe scraper)
    print("\n1. Generic JSON format:")
    generic_recipe = {
        'name': 'Chicken Salad',
        'calories': 350,
        'protein': 28,
        'carbs': 12,
        'fat': 22
        # Missing sugar and fiber
    }
    
    nutrition = parse_recipe_nutrition('generic', generic_recipe)
    print(f"   Completeness: {nutrition.get_completeness():.1%}")
    print(f"   Missing: {nutrition.get_missing_fields()}")
    print(f"   Data: {nutrition.to_dict()}")
    
    # Example 2: Very incomplete data
    print("\n2. Incomplete data (only calories):")
    incomplete = {
        'title': 'Mystery Recipe',
        'calories': 450
    }
    
    nutrition = parse_recipe_nutrition('generic', incomplete)
    print(f"   Completeness: {nutrition.get_completeness():.1%}")
    print(f"   Missing: {nutrition.get_missing_fields()}")
    
    # Example 3: Manual input
    print("\n3. Manual input:")
    nutrition = RecipeNutritionExtractor.from_manual_input(
        calories=400,
        protein=30,
        carbs=45
    )
    print(f"   Completeness: {nutrition.get_completeness():.1%}")
    print(f"   Data: {nutrition.to_dict()}")
    
    # Now use with mood/energy prediction
    print("\n" + "=" * 60)
    print("INTEGRATION WITH MOOD/ENERGY MODEL")
    print("=" * 60)
    
    # This would work with your prediction model
    from mood_energy_model import predict_both
    
    partial_nutrition = {
        'calories': 450,
        'protein_g': 25
    }
    
    mood, energy = predict_both(partial_nutrition)
    print(f"\nPrediction from partial data:")
    print(f"  Mood: {mood['label']} (confidence: {mood['confidence']:.2%})")
    print(f"  Energy: {energy['label']} (confidence: {energy['confidence']:.2%})")
    print(f"  Estimated fields: {mood['estimated_fields']}")