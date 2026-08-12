import pandas as pd
import time
import json

from db_config import get_db_connection

from core.strict_match_engine import strict_match
from core.partial_match_engine import partial_match
from core.ranking_engine import rank_recipes
from core.incompatibility_engine import (
    filter_compatible_recipes,
    get_incompatibility_warnings
)
from core.preprocessing import normalize_ingredient
from core.tfidf_algorithm import (
    calculate_idf,
    create_sparse_vector,
    calculate_cosine_similarity
)

# ==========================================
# STARTUP PHASE (RUNS ONCE)
# ==========================================

print("Loading Engine from Database...")
start_time = time.time()

# ------------------------------------------
# Load Recipes from Database
# ------------------------------------------

db = get_db_connection()
cursor = db.cursor(dictionary=True)

cursor.execute("SELECT * FROM recipes")
rows = cursor.fetchall()

cursor.close()
db.close()

df_master = pd.DataFrame(rows)

if df_master.empty:
    print("⚠ No recipes found in database.")
else:
    print(f"Loaded {len(df_master)} recipes from DB.")

# ------------------------------------------
# Safe JSON Parsing
# ------------------------------------------

def safe_json_load(x):
    try:
        if not x:
            return []
        return json.loads(x)
    except:
        return []

df_master["core_ingredients"] = df_master["core_ingredients"].apply(safe_json_load)
df_master["pantry_ingredients"] = df_master["pantry_ingredients"].apply(safe_json_load)
df_master["instructions"] = df_master["instructions"].apply(safe_json_load)

df_master["calories"] = pd.to_numeric(df_master["calories"], errors="coerce").fillna(0)
df_master["minutes"] = pd.to_numeric(df_master["minutes"], errors="coerce").fillna(30)

# ------------------------------------------
# TF-IDF PRECOMPUTATION
# ------------------------------------------

ALL_CORES = df_master["core_ingredients"].tolist()
RECIPE_LIST = df_master.to_dict("records")
RECIPE_SETS = [set(r) for r in ALL_CORES]

IDF_WEIGHTS, VOCAB_MAP = calculate_idf(ALL_CORES)

RECIPE_VECTORS = [
    create_sparse_vector(r, IDF_WEIGHTS, VOCAB_MAP)
    for r in ALL_CORES
]

print(f"Engine Ready! Index built in {time.time() - start_time:.2f}s")

# ==========================================
# MAIN RETRIEVAL FUNCTION
# ==========================================

def retrieve_recipes(user_ingredients,
                     meal_type="breakfast",
                     allergies=None,
                     strict_extra_core=0,
                     similarity_threshold=0.15,
                     top_n=5):

    if not user_ingredients:
        return None, None, "Error", "No ingredients provided.", [], [], []

    # ------------------------------------------
    # Normalize Input
    # ------------------------------------------

    user_ingredients = [normalize_ingredient(i) for i in user_ingredients]
    user_vector = create_sparse_vector(user_ingredients, IDF_WEIGHTS, VOCAB_MAP)

    warnings = get_incompatibility_warnings(user_ingredients)

    strict_display = []
    partial_display = []

    # ==========================================
    # STEP 1 — STRICT MATCH
    # ==========================================

    strict_df = strict_match(
        df_master,
        user_ingredients,
        max_extra_core=strict_extra_core
    )

    if not strict_df.empty:

        strict_df = strict_df.copy()

        similarity_scores = []

        for core_list in strict_df["core_ingredients"]:
            recipe_vector = create_sparse_vector(
                core_list,
                IDF_WEIGHTS,
                VOCAB_MAP
            )
            similarity = calculate_cosine_similarity(
                user_vector,
                recipe_vector
            )
            similarity_scores.append(similarity)

        strict_df["similarity_score"] = similarity_scores

        strict_df = filter_compatible_recipes(
            strict_df,
            ingredient_column="core_ingredients"
        )

        # --- Allergy Filter ---
        if allergies:
            allergies_norm = [normalize_ingredient(a) for a in allergies]

            def is_safe(row):
                joined = row["core_ingredients"] + row["pantry_ingredients"]
                joined = [normalize_ingredient(i) for i in joined]
                return not any(a in joined for a in allergies_norm)
            strict_df = strict_df[strict_df.apply(is_safe, axis=1)]

        if not strict_df.empty:
            strict_display = strict_df.sort_values(
                by="similarity_score",
                ascending=False
            ).head(top_n).to_dict("records")

    # ==========================================
    # STEP 2 — PARTIAL MATCH (EXCLUDE STRICT)
    # ==========================================

    partial_results = partial_match(
        user_ingredients=user_ingredients,
        recipes_list=RECIPE_LIST,
        recipe_vectors=RECIPE_VECTORS,
        recipe_sets=RECIPE_SETS,
        idf_weights=IDF_WEIGHTS,
        vocab_map=VOCAB_MAP,
        threshold=similarity_threshold
    )

    if partial_results:

        partial_df = pd.DataFrame(partial_results)

        # Exclude strict match recipes
        if strict_display:
            strict_names = {r["name"] for r in strict_display}
            partial_df = partial_df[
                ~partial_df["name"].isin(strict_names)
            ]

        partial_df = filter_compatible_recipes(
            partial_df,
            ingredient_column="core_ingredients"
        )

        # --- Allergy Filter ---
        if allergies:
            allergies_norm = [normalize_ingredient(a) for a in allergies]

            def is_safe(row):
                joined = row["core_ingredients"] + row["pantry_ingredients"]
                joined = [normalize_ingredient(i) for i in joined]
                return not any(a in joined for a in allergies_norm)
            partial_df = partial_df[partial_df.apply(is_safe, axis=1)]

        if not partial_df.empty:
            partial_display = partial_df.sort_values(
                by="similarity_score",
                ascending=False
            ).head(top_n).to_dict("records")

    # ==========================================
    # FINAL MAIN RECIPE SELECTION
    # ==========================================

    combined_candidates = strict_display if strict_display else partial_display

    if not combined_candidates:
        return None, None, "No Match", "No recipes found.", warnings, [], []

    candidates_df = pd.DataFrame(combined_candidates)

    main_recipe, ranked_recipes = rank_recipes(
        candidates_df,
        meal_type
    )

    if not ranked_recipes:
        return None, None, "No Match", "No suitable recipes found.", warnings, [], []

    # ==========================================
    # HEALTHY ALTERNATIVE
    # ==========================================

    others = [
        r for r in ranked_recipes
        if r["name"] != main_recipe["name"]
    ]

    healthy_recipe = None

    if others:
        healthy_recipe = min(
            others,
            key=lambda x: x.get("calories", 0)
        )

    return (
        main_recipe,
        healthy_recipe,
        "Strict Match" if strict_display else "Partial Match",
        "Recipes retrieved successfully.",
        warnings,
        strict_display,
        partial_display
    )