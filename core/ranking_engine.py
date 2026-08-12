def rank_recipes(candidates, meal_type="breakfast"):
    """
    Ranking logic for main recipe and display list.
    Healthy alternative handled separately.
    """

    if len(candidates) == 0:
        return None, []

    candidates = candidates.copy()

    # ----------------------------
    # BREAKFAST: max 20 min filter
    # ----------------------------
    if meal_type == "breakfast":
        candidates = candidates[candidates["minutes"] <= 20]

        if candidates.empty:
            return None, []

        candidates = candidates.sort_values(
            by=["minutes", "calories"],
            ascending=[True, True]
        )

    # ----------------------------
    # LUNCH
    # ----------------------------
    elif meal_type == "lunch":
        candidates = candidates.sort_values(
            by=["calories"],
            ascending=[False]
        )

    # ----------------------------
    # DINNER
    # ----------------------------
    elif meal_type == "dinner":
        candidates = candidates.sort_values(
            by=["calories", "minutes"],
            ascending=[True, True]
        )

    else:
        candidates = candidates.sort_values(
            by=["calories", "minutes"],
            ascending=[True, True]
        )

    main_recipe = candidates.iloc[0].to_dict()

    return main_recipe, candidates.to_dict("records")