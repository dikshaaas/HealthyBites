from core.tfidf_algorithm import calculate_cosine_similarity, create_sparse_vector
def partial_match(user_ingredients,
                  recipes_list,
                  recipe_vectors,
                  recipe_sets,
                  idf_weights,
                  vocab_map,
                  threshold=0.15):
    user_ingredients = [i.lower() for i in user_ingredients]
    user_set = set(user_ingredients)
    user_vector = create_sparse_vector(user_ingredients, idf_weights, vocab_map)
    results = []
    for i in range(len(recipes_list)):
        recipe_set = recipe_sets[i]       
        overlap_count = len(recipe_set & user_set)
        if overlap_count < 1:
            continue
        similarity = calculate_cosine_similarity(user_vector, recipe_vectors[i])
        if similarity < threshold:
            continue
        recipe_data = recipes_list[i].copy()
        recipe_data["similarity_score"] = similarity
        recipe_data["matched_count"] = overlap_count
        results.append(recipe_data)
    results.sort(key=lambda x: -x["similarity_score"])
    return results
