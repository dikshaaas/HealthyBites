from core.generation_engine import HybridRecipeGenerator

def test_generation():
    print("Initializing Generator...")
    generator = HybridRecipeGenerator()
    
    print("\nGenerating a recipe...")
    ingredients = ["chicken", "magic beans", "moon dust"]
    recipe = generator.generate_recipe(ingredients)
    
    print("\n--- GENERATED RECIPE ---")
    print(f"Title: {recipe['title']}")
    print(f"Disclaimer: {recipe['disclaimer']}")
    print("\nSteps:")
    for i, step in enumerate(recipe['steps'], 1):
        print(f"{i}. {step}")
    
    print("\nMetadata:")
    print(f"Calories: {recipe['calories']}")
    print(f"Minutes: {recipe['minutes']}")

if __name__ == "__main__":
    test_generation()
