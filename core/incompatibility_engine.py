# core/incompatibility_engine.py

import pandas as pd

# Full dictionary with messages (Common nutritional/scientific observations)
INCOMPATIBLE_PAIRS = {
    ("fish", "milk"): "Fish and milk together may cause digestive issues or skin sensitivities in some individuals.",
    ("fruit", "milk"): "Acidic fruits (citrus, berries) mixed with milk can cause curdling and acidity.",
    ("chicken", "milk"): "Combining high-protein chicken with dairy may delay digestion and cause discomfort.",
    ("honey", "boiling water"): "Heating honey to high temperatures can degrade its nutrients (Ayurvedic principle).",
    ("tea", "meat"): "Tannins in tea can inhibit the absorption of iron from meat.",
    ("spinach", "calcium"): "Oxalates in spinach can interfere with calcium absorption (if calcium-rich dairy is present).",
    ("potatoes", "rice"): "Combining two heavy starches can lead to a very high glycemic load.",
}

def get_incompatibility_warnings(ingredient_list):

    ingredients = [i.lower() for i in ingredient_list]
    warnings = []

    for pair, message in INCOMPATIBLE_PAIRS.items():
        if all(item in ingredients for item in pair):
            warnings.append(message)
    return warnings

def is_compatible(ingredient_list):

    return len(get_incompatibility_warnings(ingredient_list)) == 0

def filter_compatible_recipes(df, ingredient_column="core_ingredients"):

    return df[df[ingredient_column].apply(is_compatible)]
