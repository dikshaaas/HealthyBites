import pandas as pd
import json
try:
    df = pd.read_csv("data/processed/healthybites_master_dataset_split.csv", nrows=1)
    with open("scripts/schema_info.json", "w") as f:
        json.dump(df.columns.tolist(), f)
    print("Success")
except Exception as e:
    with open("scripts/schema_info.json", "w") as f:
        json.dump({"error": str(e)}, f)
    print("Error")
