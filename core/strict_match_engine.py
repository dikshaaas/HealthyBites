import re
def strict_match(df, user_ingredients, max_extra_core=0):
    user_set = set([u.lower() for u in user_ingredients])
    def ingredient_matches(user_item, core_item):
        words = re.findall(r'\b\w+\b', core_item.lower())
        return user_item in words
    def evaluate_recipe(core_list):
        core_lower = [item.lower() for item in core_list]
        # Check if all user ingredients are present
        for user_item in user_set:
            if not any(ingredient_matches(user_item, core_item) for core_item in core_lower):
                return None  # Not valid strict match
        # Count matched core ingredients
        matched_core = [
            core_item for core_item in core_lower
            if any(ingredient_matches(user_item, core_item) for user_item in user_set)
        ]
        extra_core_count = len(core_lower) - len(matched_core)

        if extra_core_count <= max_extra_core:
            return extra_core_count
        else:
            return None  # Too many extra ingredients
    df = df.copy()
    df["extra_core_count"] = df["core_ingredients"].apply(evaluate_recipe)
    strict_matches = df[df["extra_core_count"].notnull()]
    # PRIORITY → less extra core first
    strict_matches = strict_matches.sort_values(by="extra_core_count")
    return strict_matches
