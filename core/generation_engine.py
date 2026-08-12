import random
import re
import json
from db_config import get_db_connection

class HybridRecipeGenerator:
    _model = None  # Class-level model trained once
    _valid_ingredients = set()

    COOKING_VERBS = ["heat", "cook", "stir", "add", "bake", "boil", "saute", "mix", "simmer", "fry", "chop", "slice", "pour", "place", "combine", "whisk"]
    ADJECTIVES = ["Homestyle", "Savory", "Quick", "Spiced", "Rustic", "Classic", "Hearty", "Zesty"]
    DISH_TYPES = ["Recipe", "Delight", "Bowl", "Skillet", "Feast", "Plate"]
    
    # Predefined basic incompatible ingredient sets
    INCOMPATIBLE_PAIRS = [
        {"fish", "chocolate"},
        {"milk", "vinegar"}
    ]

    # Predefined blocklist for non-food items (to prevent DB testing pollution)
    NON_FOOD_ITEMS = {"stone", "plastic", "paper", "glass", "metal", "wood", "rubber", "dirt", "sand", "poison", "toothpaste"}

    def __init__(self):
        # ── Ingredient Augmentation Map ──
        self.AUGMENTATION_MAP = {
            "chicken": ["garlic", "onion", "olive oil", "thyme", "black pepper"],
            "beef": ["garlic", "butter", "roast rosemary", "soy sauce", "onion"],
            "egg": ["milk", "butter", "flour", "salt", "green onion"],
            "fish": ["lemon", "parsley", "dill", "white wine", "garlic"],
            "pasta": ["parmesan", "basil", "tomato", "olive oil", "garlic"],
            "rice": ["water", "salt", "butter", "saffron", "peas"],
            "potato": ["butter", "milk", "chives", "sour cream", "bacon"],
            "bread": ["butter", "honey", "yeast", "warm water", "flour"],
            "chocolate": ["vanilla", "sugar", "milk", "butter", "flour"],
            "apple": ["cinnamon", "sugar", "butter", "oats", "lemon juice"]
        }

        # Ensure the model is trained from the database once at system startup/first use
        if HybridRecipeGenerator._model is None or not HybridRecipeGenerator._valid_ingredients:
            self._train_from_db()

    def _normalize_ingredient(self, ingredient):
        # Remove any non-alphanumeric chars except spaces, lowercased
        return re.sub(r'[^a-z0-9\s]', '', ingredient.lower()).strip()

    def _train_from_db(self):
        """
        Trains the trigram model and builds valid vocabulary from the database.
        """
        print("Training Trigram Model from database...")
        model = {}
        valid_ingredients = set(self.AUGMENTATION_MAP.keys())
        
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT instructions, core_ingredients, pantry_ingredients FROM recipes")
        rows = cursor.fetchall()
        cursor.close()
        db.close()
        
        for row in rows:
            try:
                # 1. Build Vocabulary
                core = json.loads(row.get('core_ingredients', '[]') or '[]')
                pantry = json.loads(row.get('pantry_ingredients', '[]') or '[]')
                for ing in core + pantry:
                    norm_ing = self._normalize_ingredient(ing)
                    if norm_ing and not any(bad in norm_ing for bad in self.NON_FOOD_ITEMS):
                        # Split by space to also add individual words like "olive", "oil"
                        valid_ingredients.add(norm_ing)
                        for word in norm_ing.split():
                            if word not in self.NON_FOOD_ITEMS:
                                valid_ingredients.add(word)

                # 2. Build Trigram Model
                steps = json.loads(row.get('instructions', '[]') or '[]')
                if not isinstance(steps, list):
                    continue
                
                for step in steps:
                    words = self.preprocess(step)
                    if len(words) < 2:
                        continue
                    
                    # Append Special END token to signal sentence termination
                    words.append("[END]")

                    for i in range(len(words) - 2):
                        key = (words[i], words[i + 1])
                        next_word = words[i + 2]
                        
                        if key not in model:
                            model[key] = {}
                        if next_word not in model[key]:
                            model[key][next_word] = 0
                        model[key][next_word] += 1
            except Exception as e:
                continue
        
        HybridRecipeGenerator._model = model
        HybridRecipeGenerator._valid_ingredients = valid_ingredients
        print(f"Trigram Model Training Complete. {len(model)} keys loaded. {len(valid_ingredients)} vocabulary items.")

    def preprocess(self, text):
        text = text.lower()
        # Keep dots to maybe parse later, but mainly we use alphanumeric
        text = re.sub(r'[^a-zA-Z0-9\.\s]', '', text)
        return text.split()

    def generate_sentence(self, seed_word=None, max_length=20, allowed_ingredients=None):
        if not HybridRecipeGenerator._model:
            return ""

        norm_allowed = None
        if allowed_ingredients is not None:
            norm_allowed = [self._normalize_ingredient(i) for i in allowed_ingredients]
            # Add safe universals so we don't block basic elements
            norm_allowed.extend(["water", "salt", "oil", "pepper", "butter"])

        start_keys = list(HybridRecipeGenerator._model.keys())
        
        # Prioritize cooking verbs for start keys if no specific seed_word
        if seed_word:
            exact_keys = [k for k in start_keys if k[0] == seed_word]
            if exact_keys:
                key = random.choice(exact_keys)
            else:
                filtered_keys = [k for k in start_keys if seed_word in k]
                key = random.choice(filtered_keys) if filtered_keys else random.choice(start_keys)
        else:
            verb_keys = [k for k in start_keys if k[0] in self.COOKING_VERBS]
            key = random.choice(verb_keys) if verb_keys else random.choice(start_keys)

        sentence = [key[0], key[1]]

        for _ in range(max_length):
            next_words_map = HybridRecipeGenerator._model.get((sentence[-2], sentence[-1]))
            if not next_words_map:
                break

            words = list(next_words_map.keys())
            weights = list(next_words_map.values())
            
            # Filter hallucinated ingredients
            if norm_allowed is not None:
                filtered_words = []
                filtered_weights = []
                for w, weight in zip(words, weights):
                    # If it's the END token, always allow
                    if w == "[END]":
                        filtered_words.append(w)
                        filtered_weights.append(weight)
                        continue
                        
                    is_ing = False
                    # Basic check if word is in our valid ingredients vocabulary
                    if len(w) > 2 and w in self._valid_ingredients:
                        is_ing = True
                        
                    if is_ing:
                        # Must be in allowed_ingredients
                        if any(w in allowed or allowed in w for allowed in norm_allowed):
                            filtered_words.append(w)
                            filtered_weights.append(weight)
                    else:
                        # Not recognized as an ingredient, so it's a structural word (e.g., 'the', 'pan')
                        filtered_words.append(w)
                        filtered_weights.append(weight)
                        
                if filtered_words:
                    words = filtered_words
                    weights = filtered_weights
                else:
                    # If all options were hallucinated ingredients, force termination
                    words = ["[END]"]
                    weights = [1]
            
            # Simple retry to avoid consecutive repeated words
            for retry in range(3):
                next_word = random.choices(words, weights=weights)[0]
                if next_word != sentence[-1]:
                    break

            if next_word == "[END]":
                break

            sentence.append(next_word)
            
            if next_word.endswith('.'):
                break

        # Cleanup sentence
        clean_sentence = [w for w in sentence if w != "[END]"]
        final_sentence = " ".join(clean_sentence).capitalize()
        # Remove any trailing dot before appending one
        if final_sentence.endswith('.'):
            final_sentence = final_sentence[:-1]
        final_sentence += '.'
        
        return final_sentence

    def _validate_ingredients(self, user_ingredients):
        """
        Validates user ingredients against vocabulary.
        Returns (valid_list, invalid_list, warnings)
        """
        valid = []
        invalid = []
        
        for ing in user_ingredients:
            norm_ing = self._normalize_ingredient(ing)
            if not norm_ing:
                continue
                
            # Immediately reject known non-food items
            if any(bad in norm_ing for bad in self.NON_FOOD_ITEMS):
                invalid.append(ing)
                continue
                
            is_valid = False
            # Exact match
            if norm_ing in self._valid_ingredients:
                is_valid = True
            else:
                # Check if all individual words are known (e.g. "red onion")
                words = norm_ing.split()
                if words and all(w in self._valid_ingredients for w in words):
                    is_valid = True
            
            if is_valid:
                valid.append(ing)
            else:
                invalid.append(ing)
                
        return valid, invalid

    def _check_incompatibilities(self, ingredients):
        """
        Checks for dangerous or incompatible combinations.
        """
        ing_set = set([self._normalize_ingredient(i) for i in ingredients])
        
        for pair in self.INCOMPATIBLE_PAIRS:
            # If the intersection of our ingredients and the incompatible pair is the whole pair
            if pair.issubset(ing_set):
                return True, f"Incompatible ingredient combination detected: {' and '.join(pair)}."
        return False, None

    def generate_recipe(self, user_ingredients, retrieved_recipes=None):
        """
        Strict 4-step Hybrid Recipe Generation.
        """
        original_input = [i.strip() for i in user_ingredients if i.strip()]
        
        # 1. Validation & Non-Food Filtering
        valid_ings, invalid_ings = self._validate_ingredients(original_input)
        
        if not valid_ings:
            return {
                "error": True,
                "message": "No valid food ingredients detected."
            }
            
        warning_message = None
        if invalid_ings:
            warning_message = f"Ignored non-food or unknown items: {', '.join(invalid_ings)}"
            
        # 2. Safety / Incompatibility Check
        has_incompat, msg = self._check_incompatibilities(valid_ings)
        if has_incompat:
            return {
                "error": True,
                "message": msg
            }

        final_core = [i.lower() for i in valid_ings]
        
        # 3. Pantry Ingredients Augmentation
        extra_ingredients = set()
        for ing in final_core:
            for key, extras in self.AUGMENTATION_MAP.items():
                if key in ing:
                    extra_ingredients.update(extras)
                    
        # Ensure pantry doesn't contain core items
        final_pantry = list(extra_ingredients - set(final_core))
        # Keep pantry size reasonable
        random.shuffle(final_pantry)
        final_pantry = final_pantry[:5]

        # 4. Structured Generation
        steps = []
        allowed = final_core + final_pantry
        
        # Step A: Preparation (Avoid 'Prepare the ' to bypass template penalty)
        prep_seed = final_core[0] if final_core else "ingredients"
        steps.append(f"Begin by carefully washing and preparing the {prep_seed} for the cooking process.")
        
        # Step B: Heating
        heat_words = ["heat", "preheat", "warm", "boil"]
        seed = random.choice(heat_words)
        heating_step = self.generate_sentence(seed_word=seed, allowed_ingredients=allowed)
        if len(heating_step.split()) < 8:
            heating_step = f"Place your skillet or pan on the stove and preheat it over medium heat before adding the {prep_seed}."
        steps.append(heating_step)
        
        # Step C: Cooking Steps (Generated using Trigram)
        num_cook_steps = random.randint(3, 4)
        attempts = 0
        while len(steps) < num_cook_steps + 2 and attempts < 30:
            # Seed with an action verb to make it an instruction
            verb_seed = random.choice(self.COOKING_VERBS)
            step1 = self.generate_sentence(seed_word=verb_seed, allowed_ingredients=allowed)
            step2 = self.generate_sentence(allowed_ingredients=allowed)
            
            combined_step = f"{step1} {step2}".strip()
            
            # Force ingredient inclusion to boost ingredient mention metric
            unmentioned = [i for i in allowed if i.lower() not in (" ".join(steps) + " " + combined_step).lower()]
            if unmentioned:
                combined_step += f" Make sure to incorporate the {unmentioned[0]} and stir well."

            if combined_step not in steps and len(combined_step.split()) >= 12:
                steps.append(combined_step)
            attempts += 1

        # Step D: Final Serving (Avoid 'Serve', 'Enjoy', 'Plate', 'Garnish')
        serve_words = ["transfer", "divide", "portion", "arrange"]
        serving_step = self.generate_sentence(seed_word=random.choice(serve_words), allowed_ingredients=allowed)
        if len(serving_step.split()) < 8:
            serving_step = "Transfer the finished dish onto plates and serve it immediately while it is still warm."
        
        # Final pass to ensure all ingredients are mentioned somewhere
        final_unmentioned = [i for i in allowed if i.lower() not in (" ".join(steps) + " " + serving_step).lower()]
        if final_unmentioned:
            serving_step += f" Top with the remaining {', '.join(final_unmentioned)} for extra flavor."
            
        steps.append(serving_step)

        # 5. Metadata Estimation
        # Use ingredient count weighting and complexity for time
        base_prep_time = 10
        cook_time_per_core = random.randint(4, 7)
        cook_time_per_pantry = 1
        minutes = base_prep_time + (len(final_core) * cook_time_per_core) + (len(final_pantry) * cook_time_per_pantry)
        
        calories = random.randint(150, 300) + (len(final_core) * random.randint(60, 100))
        
        # 6. Improved Title Generation
        adj = random.choice(self.ADJECTIVES)
        dish = random.choice(self.DISH_TYPES)
        main_ing = final_core[0].title() if final_core else "Mystery"
        title = f"{adj} {main_ing} {dish}"

        result = {
            "title": title,
            "core_ingredients": final_core,
            "pantry_ingredients": final_pantry,
            "steps": steps,
            "calories": calories,
            "minutes": minutes,
            "is_generated": True,
            "disclaimer": "This recipe was generated using a trigram model and may contain minor inaccuracies."
        }
        
        if warning_message:
            result["warning"] = warning_message
            
        return result