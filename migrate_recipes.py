import pandas as pd
import ast
import json
from db_config import get_db_connection

# Load CSV
df = pd.read_csv("data/processed/healthybites_master_dataset_split.csv")

# Take 10k sample
df_sample = df.sample(n=70000, random_state=42)

db = get_db_connection()
cursor = db.cursor()

for _, row in df_sample.iterrows():

    # Convert string list → actual list
    core = ast.literal_eval(row["core_ingredients"])
    pantry = ast.literal_eval(row["pantry_ingredients"])
    instructions = ast.literal_eval(row["instructions"])

    cursor.execute("""
        INSERT INTO recipes 
        (name, core_ingredients, pantry_ingredients, instructions, calories, minutes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        row["name"],
        json.dumps(core),
        json.dumps(pantry),
        json.dumps(instructions),
        float(row["calories"]) if pd.notna(row["calories"]) else 0,
        int(row["minutes"]) if pd.notna(row["minutes"]) else 30
    ))

db.commit()
cursor.close()
db.close()

print("Migration completed successfully.")