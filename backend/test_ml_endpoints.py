"""
Test script for ML prediction endpoints.
Run this after starting the FastAPI server.
"""
import requests
import json

BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port

def test_predict_mood_energy_complete():
    """Test with complete nutrition data."""
    print("\n" + "="*60)
    print("TEST 1: Complete Nutrition Data")
    print("="*60)
    
    data = {
        "nutrition": {
            "calories": 450,
            "protein_g": 25,
            "carbs_g": 50,
            "fat_g": 15,
            "sugar_g": 8
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/predict-mood-energy", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Mood: {result['mood']['label']} (confidence: {result['mood']['confidence']:.2%})")
        print(f"Energy: {result['energy']['label']} (confidence: {result['energy']['confidence']:.2%})")
        print(f"Data quality: {result['mood']['data_quality']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_predict_mood_energy_partial():
    """Test with partial nutrition data (only calories)."""
    print("\n" + "="*60)
    print("TEST 2: Partial Nutrition Data (calories only)")
    print("="*60)
    
    data = {
        "nutrition": {
            "calories": 450
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/predict-mood-energy", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Mood: {result['mood']['label']} (confidence: {result['mood']['confidence']:.2%})")
        print(f"Energy: {result['energy']['label']} (confidence: {result['energy']['confidence']:.2%})")
        print(f"Estimated fields: {result['mood']['estimated_fields']}")
        print(f"Data quality: {result['mood']['data_quality']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_import_recipe_generic():
    """Test recipe import with generic format."""
    print("\n" + "="*60)
    print("TEST 3: Import Recipe (Generic Format)")
    print("="*60)
    
    data = {
        "source": "generic",
        "recipe_data": {
            "name": "Chicken Salad",
            "calories": 350,
            "protein": 28,
            "carbs": 12,
            "fat": 22
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/import-recipe", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Nutrition completeness: {result['completeness']:.1%}")
        print(f"Missing fields: {result['missing_fields']}")
        print(f"Mood: {result['predictions']['mood']['label']}")
        print(f"Energy: {result['predictions']['energy']['label']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_health_check():
    """Test the health check endpoint."""
    print("\n" + "="*60)
    print("TEST 4: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/ml/health")
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Status: {result['status']}")
        print(f"Models loaded: {result['models_loaded']}")
        print(f"Message: {result['message']}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


def test_alternative_field_names():
    """Test with alternative field naming conventions."""
    print("\n" + "="*60)
    print("TEST 5: Alternative Field Names")
    print("="*60)
    
    data = {
        "nutrition": {
            "calories": 400,
            "protein": 20,  # Without '_g' suffix
            "carbs": 45,    # Without '_g' suffix
            "fat": 12       # Without '_g' suffix
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/predict-mood-energy", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Mood: {result['mood']['label']} (confidence: {result['mood']['confidence']:.2%})")
        print(f"Energy: {result['energy']['label']} (confidence: {result['energy']['confidence']:.2%})")
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    print("="*60)
    print("ML PREDICTION ENDPOINTS TEST SUITE")
    print("="*60)
    print(f"Testing server at: {BASE_URL}")
    
    try:
        # Test health check first
        test_health_check()
        
        # Test various scenarios
        test_predict_mood_energy_complete()
        test_predict_mood_energy_partial()
        test_import_recipe_generic()
        test_alternative_field_names()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to server.")
        print(f"   Make sure the FastAPI server is running at {BASE_URL}")
        print("   Start it with: uvicorn main:app --reload")
