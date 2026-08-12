# core/test.py

from core.retrieval_engine import retrieve_recipes

# ------------------------
# Example user input
# ------------------------
user_input = ["beef", "onion", "rice", "bread"]
meal_type = "lunch"  # Used internally in ranking

# Call the retrieval engine
main, healthy, match_type, message = retrieve_recipes(user_input, meal_type=meal_type)

# ------------------------
# Print match type and message
# ------------------------
print("\nMatch Type:", match_type)
print("Message:", message)

# ------------------------
# Print the main recipe
# ------------------------
if main is not None:
    print("\n========== MAIN RECIPE ==========")
    print("Name:", main.get("name"))
    print("Calories:", main.get("calories"))
    print("Core Ingredients:", main.get("core_ingredients"))
    print("Pantry Ingredients:", main.get("pantry_ingredients"))

# ------------------------
# Print the healthy alternative
# ------------------------
if healthy is not None:
    print("\n========== HEALTHY ALTERNATIVE ==========")
    print("Name:", healthy.get("name"))
    print("Calories:", healthy.get("calories"))
    print("Core Ingredients:", healthy.get("core_ingredients"))
    print("Pantry Ingredients:", healthy.get("pantry_ingredients"))
