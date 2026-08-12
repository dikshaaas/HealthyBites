from generation_engine import HybridRecipeGenerator

def test_generation():
    generator = HybridRecipeGenerator()
    
    # Test protein augmentation
    user_ings = ["chicken"]
    recipe = generator.generate_recipe(user_ings)
    
    print("\n--- TEST: CHICKEN RECIPE ---")
    print(f"Title: {recipe['title']}")
    print(f"Core Ingredients: {recipe['core_ingredients']}")
    print(f"Pantry Ingredients: {recipe['pantry_ingredients']}")
    print(f"Steps: {recipe['steps']}")
    print(f"Calories: {recipe['calories']}")
    print(f"Minutes: {recipe['minutes']}")
    
    # Assertions
    assert "garlic" in recipe["pantry_ingredients"] or "onion" in recipe["pantry_ingredients"]
    assert len(recipe["steps"]) >= 4
    assert recipe["calories"] > 200
    assert recipe["minutes"] > 15

    # Test grain augmentation
    user_ings = ["rice"]
    recipe = generator.generate_recipe(user_ings)
    
    print("\n--- TEST: RICE RECIPE ---")
    print(f"Title: {recipe['title']}")
    print(f"Pantry Ingredients: {recipe['pantry_ingredients']}")
    
    assert "water" in recipe["pantry_ingredients"]
    
    print("\n--- SUCCESS: ALL TESTS PASSED ---")

if __name__ == "__main__":
    test_generation()
