import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.retrieval_engine import retrieve_recipes

def test_allergy():
    # Test case: Search for chicken, but allergic to garlic
    # We need to know if there's a chicken recipe with garlic in the DB
    # Since I can't query the DB directly easily without running, 
    # I'll just check if the function handles the allergy parameter correctly.
    
    ingredients = ["chicken"]
    allergies = ["garlic"]
    
    print(f"Searching for {ingredients} with allergies: {allergies}")
    
    try:
        main, healthy, match_type, message, warnings, strict, partial = retrieve_recipes(
            ingredients, 
            meal_type="dinner", 
            allergies=allergies
        )
        
        print(f"Match Type: {match_type}")
        print(f"Message: {message}")
        
        if main:
            print(f"Main Recipe: {main['name']}")
            all_ingredients = main['core_ingredients'] + main['pantry_ingredients']
            print(f"Ingredients: {all_ingredients}")
            
            contains_allergy = any("garlic" in i.lower() for i in all_ingredients)
            if contains_allergy:
                print("❌ FAILED: Recipe contains allergic ingredient!")
            else:
                print("✅ PASSED: Recipe does not contain allergic ingredient.")
        else:
            print("No recipes found (this might be fine if all matches had garlic).")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_allergy()
