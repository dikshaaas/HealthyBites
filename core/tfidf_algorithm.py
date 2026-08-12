# core/tfidf_algorithm.py

from math import log, sqrt
from collections import Counter


def calculate_idf(all_recipes_ingredients):

    N = len(all_recipes_ingredients)

    recipe_sets = [set(r) for r in all_recipes_ingredients]

    vocab = sorted(set(item for r in all_recipes_ingredients for item in r))
    vocab_map = {word: i for i, word in enumerate(vocab)}

    idf_weights = {}

    for word in vocab:
        df = sum(1 for r_set in recipe_sets if word in r_set)
        idf_weights[word] = log((N + 1) / (df + 1)) + 1

    return idf_weights, vocab_map


def create_sparse_vector(ingredients, idf_weights, vocab_map):
# Sparse vector: Stores only ingredients with non-zero 
# TF-IDF values, ignoring zero entries to save memory.
    count = Counter(ingredients)
    vector = {}

    for word, freq in count.items():
        if word in vocab_map:
            idx = vocab_map[word]
            vector[idx] = freq * idf_weights[word]

    return vector


def calculate_cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0
    dot_product = sum(
        vec1[idx] * vec2[idx]
        for idx in vec1
        if idx in vec2
    )
    mag1 = sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = sqrt(sum(v ** 2 for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot_product / (mag1 * mag2)
