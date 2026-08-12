def normalize_ingredient(ingredient):

    ingredient = ingredient.lower().strip()

    # Normalization mapping for common variations
    # This could be expanded or moved to a configuration file/database
    NORMALIZATION_MAP = {
        "beef": ["ground beef", "beef steak", "beef cubes", "roast beef"],
        "chicken": ["chicken breast", "chicken thighs", "chicken wings", "ground chicken"],
        "pork": ["pork loin", "pork chops", "ground pork", "bacon", "ham"],
        "lamb": ["lamb chops", "ground lamb", "lamb leg"],
        "turkey": ["ground turkey", "turkey breast"],
        "fish": ["salmon", "tuna", "cod", "tilapia", "whitefish"],
        "shrimp": ["prawns", "shrimp tails"],
        "rice": ["white rice", "brown rice", "basmati", "jasmine rice"],
        "milk": ["whole milk", "skim milk", "dairy milk"],
        "flour": ["all-purpose flour", "whole wheat flour", "bread flour"],
        "onion": ["red onion", "white onion", "yellow onion", "shallots"]
    }

    # Inverse mapping for efficient lookup
    for base, variants in NORMALIZATION_MAP.items():
        if ingredient == base or any(variant in ingredient for variant in variants):
            return base

    return ingredient


def preprocess_input(user_input):
    if isinstance(user_input, str):
        ingredients = user_input.lower().split(",")
        ingredients = [item.strip() for item in ingredients if item.strip()]
        return ingredients
    return []