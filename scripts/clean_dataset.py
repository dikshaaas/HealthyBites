import pandas as pd
import ast
import os

RAW_PATH = "data/raw/RAW_recipes.csv"
OUTPUT_PATH = "data/processed/clean_recipes.csv"

print("Loading dataset...")
df = pd.read_csv(RAW_PATH)

print("Original shape:", df.shape)

# Remove rows with missing important data
df = df.dropna(subset=["ingredients", "nutrition", "steps"])

# Convert ingredients column from string to list
df["ingredients"] = df["ingredients"].apply(ast.literal_eval)

# Convert steps column from string to list
df["steps"] = df["steps"].apply(ast.literal_eval)

# Extract calories
def extract_calories(nutrition_str):
    try:
        nutrition_list = ast.literal_eval(nutrition_str)
        return float(nutrition_list[0])  # First value = calories
    except:
        return None

df["calories"] = df["nutrition"].apply(extract_calories)

# Remove rows where calorie extraction failed
df = df.dropna(subset=["calories"])

# Keep only required columns
df = df[["id", "name", "minutes", "ingredients", "steps", "calories"]]

# Remove duplicate recipes
df = df.drop_duplicates(subset=["name"])

print("Cleaned shape:", df.shape)

# Create processed folder if not exists
os.makedirs("data/processed", exist_ok=True)

# Save cleaned dataset
df.to_csv(OUTPUT_PATH, index=False)

print("Dataset cleaned and saved successfully!")
