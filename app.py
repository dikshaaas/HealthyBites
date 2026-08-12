from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
from db_config import get_db_connection
from core.retrieval_engine import retrieve_recipes
from core.generation_engine import HybridRecipeGenerator
import inspect
print(f"DEBUG: retrieve_recipes signature: {inspect.signature(retrieve_recipes)}")
import json

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"
app.config['UPLOAD_FOLDER'] = 'static/uploads/profiles'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db_settings():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                id INT PRIMARY KEY, 
                hero_title TEXT, 
                hero_subtitle TEXT, 
                hero_tags TEXT,
                primary_color VARCHAR(7),
                secondary_color VARCHAR(7),
                hero_image VARCHAR(255)
            )
        """)
        
        # Add new columns if migrating from old version
        cursor.execute("SHOW COLUMNS FROM site_settings LIKE 'primary_color'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE site_settings ADD COLUMN primary_color VARCHAR(7) DEFAULT '#f97316'")
            cursor.execute("ALTER TABLE site_settings ADD COLUMN secondary_color VARCHAR(7) DEFAULT '#fbbf24'")
            cursor.execute("ALTER TABLE site_settings ADD COLUMN hero_image VARCHAR(255) DEFAULT NULL")
            db.commit()

        cursor.execute("SELECT id FROM site_settings WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO site_settings (id, hero_title, hero_subtitle, hero_tags, primary_color, secondary_color) 
                VALUES (1, 'Cook Great Meals with<br>What You Already Have', 
                        'Tell us what\\'s in your kitchen and we\\'ll suggest recipes you can make right now — no shopping needed.', 
                        'Chicken, Pasta, Eggs, Rice', '#f97316', '#fbbf24')
            """)
            db.commit()

        # Ensure generated_recipes table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_recipes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                
                title VARCHAR(255),
                
                core_ingredients TEXT,
                pantry_ingredients TEXT,
                steps LONGTEXT,
                
                calories INT,
                minutes INT,
                
                input_ingredients TEXT,
                
                source VARCHAR(50) DEFAULT 'fallback',
                
                disclaimer TEXT,
                
                is_approved BOOLEAN DEFAULT NULL,
                
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX (user_id)
            )
        """)
        db.commit()

        # Auto-migrate generated_recipes if we created it previously without new columns
        try:
            cursor.execute("SHOW COLUMNS FROM generated_recipes LIKE 'disclaimer'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE generated_recipes ADD COLUMN disclaimer TEXT")
                cursor.execute("ALTER TABLE generated_recipes ADD COLUMN is_approved BOOLEAN DEFAULT NULL")
                cursor.execute("ALTER TABLE generated_recipes MODIFY COLUMN steps LONGTEXT")
                db.commit()
        except Exception as e:
            print(f"Migration error for generated_recipes: {e}")

        cursor.close()
        db.close()
    except Exception as e:
        print(f"DB Init Error: {e}")


def normalize_recipe_payload(recipe):
    if not recipe:
        return None

    normalized = dict(recipe)
    for field in ("core_ingredients", "pantry_ingredients", "instructions"):
        value = normalized.get(field, [])
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = [value] if value.strip() else []
        normalized[field] = value if isinstance(value, list) else []
    return normalized
# =========================
# CONTEXT PROCESSORS
# =========================

@app.context_processor
def inject_global_data():
    current_user = None
    settings = None
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if 'user_id' in session:
        try:
            cursor.execute("SELECT username, email, profile_image FROM users WHERE id=%s", (session["user_id"],))
            current_user = cursor.fetchone()
        except:
            pass
            
    try:
        cursor.execute("SELECT * FROM site_settings WHERE id = 1")
        settings = cursor.fetchone()
    except:
        pass
        
    cursor.close()
    db.close()
    
    return dict(current_user=current_user, settings=settings)

# =========================
# DECORATORS
# =========================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


# =========================
# HOME & ABOUT
# =========================

@app.route("/about-us")
def about():
    return render_template("about.html")


@app.route("/")
def home():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT name, calories, minutes FROM recipes ORDER BY RAND() LIMIT 5")
    popular_recipes = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("home.html", popular_recipes=popular_recipes)


# =========================
# AUTH ROUTES
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 1. Validate empty fields
        if not username_or_email or not password:
            flash("Invalid username or password") # General fallback if somehow bypassed
            if not username_or_email and not password:
                flash("Please enter both username and password")
            elif not username_or_email:
                flash("Please enter your username or email")
            else:
                flash("Please enter your password")
            return render_template("login.html")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s OR email=%s",
            (username_or_email, username_or_email)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        # 2. Check if user exists
        if not user:
            flash("User not found")
            return render_template("login.html")

        # 3. Check if password is correct
        if not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password")
            flash("Please enter the correct password")
            return render_template("login.html")

        # 4. Successful login
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            db.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))
        except:
            flash("Username or Email already exists")

    return render_template("register.html")


# =========================
# SEARCH
# =========================

@app.route("/search", methods=["GET", "POST"])
@login_required
def index():

    # 🔥 CLEAR OLD RESULTS on every visit (GET or POST)
    session.pop("search_recipes", None)
    session.pop("partial_recipes", None)
    session.pop("healthy_recipe", None)
    session.pop("search_match_type", None)
    session.pop("search_message", None)
    session.pop("search_warnings", None)

    if request.method == "POST":

        ingredients = request.form["ingredients"]
        meal_type = request.form["meal_type"]
        allergies = request.form.get("allergies", "")

        user_ingredients = [i.strip() for i in ingredients.split(",")]
        user_allergies = [a.strip() for a in allergies.split(",")] if allergies.strip() else []

        main, healthy, match_type, message, warnings, strict_recipes, partial_recipes = retrieve_recipes(
            user_ingredients,
            meal_type=meal_type,
            allergies=user_allergies
        )

        if strict_recipes:
            session["search_recipes"] = strict_recipes
            session["partial_recipes"] = partial_recipes

        elif partial_recipes:
            session["search_recipes"] = partial_recipes
            session["partial_recipes"] = []

        else:
            # Move AI Generation to fallback (handled in choose_recipe.html)
            session["search_recipes"] = []
            session["partial_recipes"] = []
            session["healthy_recipe"] = None
            session["search_match_type"] = "No Match Found"
            session["search_message"] = "We couldn't find any recipes matching your ingredients in our database."
            session["search_warnings"] = warnings
            session["search_ingredients"] = ingredients # Save for AI fallback button

            return redirect(url_for("choose_recipe"))

        session["healthy_recipe"] = healthy
        session["search_match_type"] = match_type
        session["search_message"] = message
        session["search_warnings"] = warnings

        return redirect(url_for("choose_recipe"))

    return render_template("search.html")


def _save_generated_recipe(user_id, generated, input_str, source="find"):
    """Save an AI-generated recipe into the generated_recipes table."""
    if not user_id:
        return
    try:
        db = get_db_connection()
        c = db.cursor()
        c.execute("""
            INSERT INTO generated_recipes
                (user_id, title, core_ingredients, pantry_ingredients,
                 steps, calories, minutes, input_ingredients, source, disclaimer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            generated.get("title"),
            json.dumps(generated.get("core_ingredients", [])),
            json.dumps(generated.get("pantry_ingredients", [])),
            json.dumps(generated.get("steps", [])),
            generated.get("calories"),
            generated.get("minutes"),
            input_str,
            source,
            generated.get("disclaimer")
        ))
        db.commit()
        c.close()
        db.close()
    except Exception as e:
        print(f"[generated_recipes] save error: {e}")


@app.route("/magic_generate", methods=["POST"])
@login_required
def magic_generate():
    ingredients = request.form.get("ingredients", "")
    user_ingredients = [i.strip() for i in ingredients.split(",")] if ingredients else []

    if not user_ingredients:
        flash("Please provide ingredients for AI generation.")
        return redirect(url_for("index"))

    generator = HybridRecipeGenerator()
    generated  = generator.generate_recipe(user_ingredients, [])

    if generated.get("error"):
        flash(generated.get("message", "We could not generate a recipe with these ingredients."))
        return redirect(url_for("index"))

    main_recipe = {
        "name":              generated["title"],
        "core_ingredients":  generated["core_ingredients"],
        "pantry_ingredients":generated["pantry_ingredients"],
        "instructions":      generated["steps"],
        "calories":          generated["calories"],
        "minutes":           generated["minutes"],
        "is_generated":      True,
        "disclaimer":        generated.get("disclaimer", "")
    }

    # Persist to generated_recipes (source = magic)
    _save_generated_recipe(
        session.get("user_id"), generated, ingredients, source="magic"
    )

    session["search_recipes"]   = [main_recipe]
    session["partial_recipes"]  = []
    session["healthy_recipe"]   = None
    session["search_match_type"] = "AI Recipe Generation"
    session["search_message"] = "Our AI engine has generated a custom recipe based on your available ingredients."
    
    warnings = []
    if "warning" in generated:
        warnings.append(generated["warning"])
    session["search_warnings"]  = warnings

    return redirect(url_for("choose_recipe"))


# =========================
# CHOOSE RECIPE
# =========================

@app.route("/choose_recipe")
@login_required
def choose_recipe():

    recipes = session.get("search_recipes", [])
    partial_recipes = session.get("partial_recipes", [])

    # Allow empty recipes for fallback UI
    pass

    return render_template(
        "choose_recipe.html",
        recipes=recipes,
        partial_recipes=partial_recipes,
        healthy=session.get("healthy_recipe"),
        match_type=session.get("search_match_type"),
        message=session.get("search_message"),
        warnings=session.get("search_warnings")
    )


# =========================
# RECIPE DETAIL (FIXED)
# =========================

@app.route("/recipe/<path:recipe_name>")
@login_required
def recipe_detail(recipe_name):
    source = request.args.get("source", "strict")

    # 🔮 1. Check if it is an AI Generated Recipe in the Session
    ai_recipes = session.get("search_recipes", [])
    ai_match = next((r for r in ai_recipes if r.get("name") == recipe_name and r.get("is_generated")), None)

    if ai_match:
        return render_template(
            "ai_recipe_detail.html",
            main=ai_match,
            healthy=None,
            source=source
        )

    # 🥘 2. Proceed with database retrieval for standard recipes
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM recipes WHERE name=%s", (recipe_name,))
    recipe = cursor.fetchone()

    # 🤖 3. If not in recipes, check if it's a persisted AI generated recipe for this user
    if not recipe:
        cursor.execute("SELECT * FROM generated_recipes WHERE title=%s AND user_id=%s LIMIT 1", (recipe_name, session["user_id"]))
        ai_db_match = cursor.fetchone()
        
        if ai_db_match:
            # Reconstruct as if it came from session generator
            main_ai = {
                "name": ai_db_match["title"],
                "core_ingredients": json.loads(ai_db_match.get("core_ingredients") or "[]"),
                "pantry_ingredients": json.loads(ai_db_match.get("pantry_ingredients") or "[]"),
                "instructions": json.loads(ai_db_match.get("steps") or "[]"),
                "calories": ai_db_match["calories"],
                "minutes": ai_db_match["minutes"],
                "is_generated": True,
                "disclaimer": "This recipe was generated by our AI using your saved ingredients history."
            }
            cursor.close()
            db.close()
            return render_template(
                "ai_recipe_detail.html",
                main=main_ai,
                healthy=None,
                source=source
            )

    if not recipe:
        cursor.close()
        db.close()
        return "Recipe not found", 404

    recipe = normalize_recipe_payload(recipe)

    # 👁 Track Viewed
    cursor.execute(
        "INSERT INTO viewed_recipes (user_id, recipe_name) VALUES (%s, %s)",
        (session["user_id"], recipe_name)
    )
    db.commit()

    cursor.close()
    db.close()

    healthy_recipe = normalize_recipe_payload(session.get("healthy_recipe"))

    return render_template(
        "recipe_detail.html",
        main=recipe,
        healthy=healthy_recipe,
        source=source
    )


@app.route("/recipe/<path:recipe_name>/healthy")
@login_required
def healthy_recipe_detail(recipe_name):
    healthy_recipe = normalize_recipe_payload(session.get("healthy_recipe"))

    if not healthy_recipe:
        flash("No healthier alternative available for this recipe.")
        return redirect(url_for("recipe_detail", recipe_name=recipe_name))

    return render_template(
        "recipe_alternative_detail.html",
        main=healthy_recipe,
        base_recipe_name=recipe_name
    )

# =========================
# partial results
# =========================


@app.route("/partial_results")
@login_required
def partial_results():

    partial_recipes = session.get("partial_recipes", [])

    if not partial_recipes:
        flash("No partial matches available.")
        return redirect(url_for("choose_recipe"))

    return render_template(
        "partial_results.html",
        recipes=partial_recipes
    )


# =========================
# SAVE RECIPE
# =========================

@app.route("/save_recipe", methods=["POST"])
@login_required
def save_recipe():
    recipe_name = request.form["recipe_name"]

    db = get_db_connection()
    cursor = db.cursor()

    # Check if already saved to prevent duplicates
    cursor.execute("SELECT 1 FROM saved_recipes WHERE user_id=%s AND recipe_name=%s", (session["user_id"], recipe_name))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash("Recipe is already in your collection.")
        return redirect(url_for("dashboard"))

    cursor.execute(
        "INSERT INTO saved_recipes (user_id, recipe_name) VALUES (%s, %s)",
        (session["user_id"], recipe_name)
    )
    db.commit()
    cursor.close()
    db.close()

    flash("Recipe saved successfully.")
    return redirect(url_for("dashboard"))


# =========================
# USER DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Group by recipe_name to avoid duplication from multiple generation entries
    cursor.execute("""
        SELECT s.recipe_name, 
               MAX(COALESCE(r.calories, g.calories)) as calories, 
               MAX(COALESCE(r.minutes, g.minutes)) as minutes 
        FROM saved_recipes s
        LEFT JOIN recipes r ON s.recipe_name = r.name
        LEFT JOIN generated_recipes g ON s.recipe_name = g.title AND s.user_id = g.user_id
        WHERE s.user_id=%s
        GROUP BY s.recipe_name
    """, (session["user_id"],))
    saved = cursor.fetchall()

    cursor.execute("""
        SELECT v.recipe_name, 
               COALESCE(r.calories, g.calories) as calories, 
               COALESCE(r.minutes, g.minutes) as minutes 
        FROM viewed_recipes v
        LEFT JOIN recipes r ON v.recipe_name = r.name
        LEFT JOIN generated_recipes g ON v.recipe_name = g.title AND v.user_id = g.user_id
        WHERE v.user_id=%s 
        ORDER BY v.id DESC LIMIT 10
    """, (session["user_id"],))
    viewed = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        saved=saved,
        viewed=viewed
    )


@app.route("/unsave_recipe/<path:recipe_name>")
@login_required
def unsave_recipe(recipe_name):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM saved_recipes WHERE user_id=%s AND recipe_name=%s",
        (session["user_id"], recipe_name)
    )
    db.commit()
    flash("Recipe removed from favourites.")
    return redirect(url_for("dashboard"))


# =========================
# PROFILE
# =========================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            username = request.form["username"]
            email = request.form["email"]
            
            # 🖼 Handle Profile Picture Upload or Removal
            profile_image_path = None
            remove_image = request.form.get("remove_image") == "true"
            
            if not remove_image and 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_image_path = f"uploads/profiles/{filename}"

            try:
                if remove_image:
                    cursor.execute(
                        "UPDATE users SET username=%s, email=%s, profile_image=NULL WHERE id=%s",
                        (username, email, session["user_id"])
                    )
                elif profile_image_path:
                    cursor.execute(
                        "UPDATE users SET username=%s, email=%s, profile_image=%s WHERE id=%s",
                        (username, email, profile_image_path, session["user_id"])
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET username=%s, email=%s WHERE id=%s",
                        (username, email, session["user_id"])
                    )
                db.commit()
                session["username"] = username
                if remove_image:
                    flash("Profile picture removed.")
                else:
                    flash("Profile updated successfully.")
            except Exception as e:
                flash(f"Update failed: {str(e)}")

        elif action == "change_password":
            current_pw = request.form["current_password"]
            new_pw = request.form["new_password"]

            cursor.execute("SELECT password_hash FROM users WHERE id=%s", (session["user_id"],))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], current_pw):
                new_hash = generate_password_hash(new_pw)
                cursor.execute(
                    "UPDATE users SET password_hash=%s WHERE id=%s",
                    (new_hash, session["user_id"])
                )
                db.commit()
                flash("Password changed successfully.")
            else:
                flash("Current password is incorrect.")

        return redirect(url_for("profile"))

    cursor.execute("SELECT username, email, profile_image FROM users WHERE id=%s", (session["user_id"],))
    user = cursor.fetchone()
    return render_template("profile.html", user=user)

    # =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # ---------- COUNTS ----------
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM recipes")
    total_recipes = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM saved_recipes")
    total_saved = cursor.fetchone()["total"]

    # ---------- BAR CHART (Saved Recipes per User) ----------
    cursor.execute("""
        SELECT u.username, COUNT(s.id) as saved_count
        FROM users u
        LEFT JOIN saved_recipes s ON u.id = s.user_id
        GROUP BY u.id
    """)
    user_data = cursor.fetchall()

    chart_labels = [row["username"] for row in user_data]
    chart_data = [row["saved_count"] for row in user_data]

    # ---------- DOUGHNUT CHART (Admin vs User Count) ----------
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role='admin'")
    admin_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role='user'")
    user_count = cursor.fetchone()["count"]

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_recipes=total_recipes,
        total_saved=total_saved,
        chart_labels=chart_labels,
        chart_data=chart_data,
        admin_count=admin_count,
        user_count=user_count
    )

# =========================
# ADMIN USERS
# =========================
# =========================
# ADMIN - MANAGE USERS
# =========================
@app.route("/admin/users")
@admin_required
def admin_users():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.id, u.username, u.email, u.role, u.profile_image,
               COUNT(s.id) AS saved_count
        FROM users u
        LEFT JOIN saved_recipes s ON u.id = s.user_id
        GROUP BY u.id
    """)

    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("admin/users.html", users=users)

@app.route("/admin/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):

    db = get_db_connection()
    cursor = db.cursor()

    # Prevent admin from deleting themselves
    if user_id == session["user_id"]:
        return redirect(url_for("admin_users"))

    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for("admin_users"))


# =========================
# ADMIN RECIPES
# =========================
# =========================
# ADMIN - MANAGE RECIPES
# =========================
@app.route("/admin/recipes")
@admin_required
def admin_recipes():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, calories, minutes
        FROM recipes
        ORDER BY id DESC
        LIMIT 100
    """)

    recipes = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("admin/recipes.html", recipes=recipes)

@app.route("/admin/delete_recipe/<int:recipe_id>")
@admin_required
def delete_recipe(recipe_id):

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("DELETE FROM recipes WHERE id=%s", (recipe_id,))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for("admin_recipes"))

@app.route("/admin/add_recipe", methods=["GET", "POST"])
@admin_required
def add_recipe():

    if request.method == "POST":

        name = request.form["name"]
        calories = request.form["calories"]
        minutes = request.form["minutes"]

        core = request.form["core"].split(",")
        pantry = request.form["pantry"].split(",")
        instructions = request.form["instructions"].split("\n")

        import json

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO recipes
            (name, core_ingredients, pantry_ingredients, instructions, calories, minutes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            name,
            json.dumps([i.strip() for i in core]),
            json.dumps([i.strip() for i in pantry]),
            json.dumps([i.strip() for i in instructions]),
            calories,
            minutes
        ))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("admin_recipes"))

    return render_template("admin/add_recipe.html")


# =========================
# ADMIN - EDIT RECIPE
# =========================
@app.route("/admin/edit_recipe/<int:recipe_id>", methods=["GET", "POST"])
@admin_required
def edit_recipe(recipe_id):

    import json

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        calories = request.form["calories"]
        minutes = request.form["minutes"]

        core = request.form["core"].split(",")
        pantry = request.form["pantry"].split(",")
        instructions = request.form["instructions"].split("\n")

        cursor.execute("""
            UPDATE recipes
            SET name=%s,
                core_ingredients=%s,
                pantry_ingredients=%s,
                instructions=%s,
                calories=%s,
                minutes=%s
            WHERE id=%s
        """, (
            name,
            json.dumps([i.strip() for i in core]),
            json.dumps([i.strip() for i in pantry]),
            json.dumps([i.strip() for i in instructions]),
            calories,
            minutes,
            recipe_id
        ))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for("admin_recipes"))

    # GET request — fetch recipe
    cursor.execute("SELECT * FROM recipes WHERE id=%s", (recipe_id,))
    recipe = cursor.fetchone()

    cursor.close()
    db.close()

    if not recipe:
        return "Recipe not found", 404

    # Convert JSON strings back to text
    recipe["core_ingredients"] = ", ".join(json.loads(recipe["core_ingredients"]))
    recipe["pantry_ingredients"] = ", ".join(json.loads(recipe["pantry_ingredients"]))
    recipe["instructions"] = "\n".join(json.loads(recipe["instructions"]))

    return render_template("admin/edit_recipe.html", recipe=recipe)

@app.route("/admin/site", methods=["GET", "POST"])
@admin_required
def admin_site_settings():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["hero_title"]
        subtitle = request.form["hero_subtitle"]
        tags = request.form["hero_tags"]
        primary_color = request.form["primary_color"]
        secondary_color = request.form["secondary_color"]
        
        # Handle Hero Image Upload
        hero_image_path = None
        if 'hero_image' in request.files:
            file = request.files['hero_image']
            if file and allowed_file(file.filename):
                os.makedirs('static/uploads/site', exist_ok=True)
                filename = secure_filename(f"hero_{file.filename}")
                file_path = os.path.join('static/uploads/site', filename)
                file.save(file_path)
                hero_image_path = f"uploads/site/{filename}"

        if hero_image_path:
            cursor.execute("""
                UPDATE site_settings 
                SET hero_title=%s, hero_subtitle=%s, hero_tags=%s, 
                    primary_color=%s, secondary_color=%s, hero_image=%s
                WHERE id=1
            """, (title, subtitle, tags, primary_color, secondary_color, hero_image_path))
        else:
            cursor.execute("""
                UPDATE site_settings 
                SET hero_title=%s, hero_subtitle=%s, hero_tags=%s, 
                    primary_color=%s, secondary_color=%s
                WHERE id=1
            """, (title, subtitle, tags, primary_color, secondary_color))
            
        db.commit()
        flash("Site settings updated successfully.")
        return redirect(url_for("admin_site_settings"))

    cursor.execute("SELECT * FROM site_settings WHERE id=1")
    settings = cursor.fetchone()
    
    cursor.close()
    db.close()
    return render_template("admin/site_settings.html", settings=settings)

# =========================
# ADMIN — VIEW USER PROFILE
# =========================

@app.route("/admin/user/<int:user_id>")
@admin_required
def admin_view_user(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, username, email, role, profile_image
        FROM users WHERE id = %s
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close(); db.close()
        return "User not found", 404

    # Liked / saved recipes
    cursor.execute("""
        SELECT s.recipe_name, 
               COALESCE(r.calories, g.calories) as calories, 
               COALESCE(r.minutes, g.minutes) as minutes
        FROM saved_recipes s
        LEFT JOIN recipes r ON s.recipe_name = r.name
        LEFT JOIN generated_recipes g ON s.recipe_name = g.title AND s.user_id = g.user_id
        WHERE s.user_id = %s
        ORDER BY s.id DESC
    """, (user_id,))
    liked = cursor.fetchall()

    # Most searched — group viewed_recipes by frequency
    cursor.execute("""
        SELECT v.recipe_name, COUNT(v.id) AS search_count, 
               COALESCE(r.calories, g.calories) as calories, 
               COALESCE(r.minutes, g.minutes) as minutes
        FROM viewed_recipes v
        LEFT JOIN recipes r ON v.recipe_name = r.name
        LEFT JOIN generated_recipes g ON v.recipe_name = g.title AND v.user_id = g.user_id
        WHERE v.user_id = %s
        GROUP BY v.recipe_name, calories, minutes
        ORDER BY search_count DESC
        LIMIT 15
    """, (user_id,))
    popular = cursor.fetchall()

    # AI-generated recipes from generated_recipes table
    ai_recipes = []
    try:
        cursor.execute("""
            SELECT id, title, core_ingredients, pantry_ingredients,
                   steps, calories, minutes, input_ingredients, source, generated_at
            FROM generated_recipes
            WHERE user_id = %s
            ORDER BY generated_at DESC
        """, (user_id,))
        for row in cursor.fetchall():
            row["core_ingredients"]   = json.loads(row["core_ingredients"]   or "[]")
            row["pantry_ingredients"] = json.loads(row["pantry_ingredients"] or "[]")
            row["steps"]              = json.loads(row["steps"]              or "[]")
            
            # Compute accuracy for inline display
            raw_input = row.get("input_ingredients", "")
            input_list = [i.strip() for i in raw_input.split(",") if i.strip()] if raw_input else []
            generated = {
                "steps": row["steps"],
                "core_ingredients": row["core_ingredients"],
                "pantry_ingredients": row["pantry_ingredients"]
            }
            row["accuracy"] = _compute_ai_accuracy(generated, input_list)
            
            ai_recipes.append(row)
    except Exception as e:
        print(f"[admin_view_user] generated_recipes error: {e}")

    cursor.close()
    db.close()

    return render_template(
        "admin/user_profile.html",
        profile_user=user,
        liked=liked,
        popular=popular,
        ai_recipes=ai_recipes
    )


@app.route("/admin/generated_recipe/<int:recipe_id>")
@admin_required
def admin_generated_detail(recipe_id):
    import json
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT g.*, u.username, u.email 
        FROM generated_recipes g
        JOIN users u ON g.user_id = u.id
        WHERE g.id = %s
    """, (recipe_id,))
    recipe = cursor.fetchone()

    if not recipe:
        cursor.close(); db.close()
        return "Recipe not found", 404

    # Process JSON for display
    recipe["core_ingredients"] = json.loads(recipe["core_ingredients"] or "[]")
    recipe["pantry_ingredients"] = json.loads(recipe["pantry_ingredients"] or "[]")
    recipe["steps"] = json.loads(recipe["steps"] or "[]")

    # Compute accuracy
    raw_input = recipe.get("input_ingredients", "")
    input_list = [i.strip() for i in raw_input.split(",") if i.strip()] if raw_input else []
    recipe["accuracy"] = _compute_ai_accuracy(recipe, input_list)

    cursor.close()
    db.close()

    return render_template("admin/generated_recipe_detail.html", recipe=recipe)


@app.route("/admin/delete_generated/<int:recipe_id>")
@admin_required
def delete_generated(recipe_id):
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("SELECT user_id FROM generated_recipes WHERE id=%s", (recipe_id,))
    row = cursor.fetchone()
    user_id = row[0] if row else None
    
    cursor.execute("DELETE FROM generated_recipes WHERE id=%s", (recipe_id,))
    db.commit()

    cursor.close()
    db.close()

    flash("Generated recipe deleted successfully.")
    if user_id:
        return redirect(url_for("admin_view_user", user_id=user_id))
    return redirect(url_for("admin_dashboard"))


# =========================
# ADMIN — AI INSPECTOR (standalone)
# =========================

@app.route("/admin/ai_inspector")
@admin_required
def admin_ai_inspector():
    return render_template("admin/ai_inspector.html")


def _compute_ai_accuracy(generated, user_ingredients):
    steps  = generated.get("steps", [])
    scores = {}

    ideal      = 5
    step_score = max(0, 100 - abs(len(steps) - ideal) * 15)
    scores["step_count"] = {"value": step_score, "label": f"{len(steps)} steps (ideal 4–6)", "icon": "📋"}

    avg_len      = sum(len(s.split()) for s in steps) / max(len(steps), 1)
    length_score = min(100, int(avg_len / 15 * 100))
    scores["step_quality"] = {"value": length_score, "label": f"{avg_len:.1f} words/step (target ≥10)", "icon": "📝"}

    templates    = ["Prepare the ", "Serve", "Enjoy", "Plate", "Garnish"]
    trig_steps   = [s for s in steps if not any(s.startswith(t) for t in templates)]
    trigram_cov  = int(len(trig_steps) / max(len(steps), 1) * 100)
    scores["trigram_coverage"] = {"value": trigram_cov, "label": f"{len(trig_steps)}/{len(steps)} trigram-generated", "icon": "🔗"}

    all_ing   = generated.get("core_ingredients", []) + generated.get("pantry_ingredients", [])
    full_text = " ".join(steps).lower()
    mentioned = sum(1 for i in all_ing if i.lower() in full_text)
    ing_score = int(mentioned / max(len(all_ing), 1) * 100)
    scores["ingredient_mention"] = {"value": ing_score, "label": f"{mentioned}/{len(all_ing)} ingredients in steps", "icon": "🥕"}

    unique    = len(set(steps))
    rep_score = int(unique / max(len(steps), 1) * 100)
    scores["uniqueness"] = {"value": rep_score, "label": f"{unique}/{len(steps)} unique steps", "icon": "✨"}

    overall = int(sum(v["value"] for v in scores.values()) / len(scores))
    grade   = ("A","#10b981") if overall>=80 else ("B","#3b82f6") if overall>=65 else ("C","#f59e0b") if overall>=50 else ("D","#ef4444")

    suggestions = []
    if step_score   < 70: suggestions.append("Aim for 4–6 structured steps per recipe.")
    if length_score < 60: suggestions.append("Steps are too short — trigram model needs richer training data.")
    if trigram_cov  < 50: suggestions.append("Most steps are templates. Add more DB recipe instructions to improve diversity.")
    if ing_score    < 50: suggestions.append("Steps don’t reference user ingredients — review seed_word selection in generate_sentence().")
    if rep_score    < 80: suggestions.append("Duplicate steps detected — add a seen-step deduplication filter.")
    if not suggestions:   suggestions.append("✅ Generator is performing well. No critical issues found.")

    return {"scores": scores, "overall": overall, "grade": grade[0], "grade_color": grade[1], "suggestions": suggestions}


@app.route("/admin/ai_test", methods=["POST"])
@admin_required
def admin_ai_test():
    raw  = request.form.get("ingredients", "")
    ings = [i.strip() for i in raw.split(",") if i.strip()]
    if not ings:
        return json.dumps({"error": "Please enter at least one ingredient."}), 400, {"Content-Type": "application/json"}

    generated = HybridRecipeGenerator().generate_recipe(ings, [])
    if generated.get("error"):
        return json.dumps({"error": generated.get("message")}), 400, {"Content-Type": "application/json"}
        
    accuracy  = _compute_ai_accuracy(generated, ings)
    return json.dumps({"recipe": generated, "accuracy": accuracy}), 200, {"Content-Type": "application/json"}


# =========================
@app.route("/api/ingredients")
@login_required
def api_ingredients():
    query = request.args.get("q", "").lower()
    if not query:
        return json.dumps([])

    db = get_db_connection()
    cursor = db.cursor()
    # We'll use a more efficient way if this grows, but for now, let's get unique ingredients
    cursor.execute("SELECT DISTINCT core_ingredients FROM recipes")
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    starts_with = set()
    contains = set()
    
    for row in rows:
        try:
            ings = json.loads(row[0])
            for ing in ings:
                ing_lower = ing.lower().strip()
                if ing_lower.startswith(query):
                    starts_with.add(ing.strip().capitalize())
                elif query in ing_lower:
                    contains.add(ing.strip().capitalize())
        except:
            continue

    # Combine: prioritize starts_with, then fills with contains
    suggestions = sorted(list(starts_with)) + sorted(list(contains))
    return json.dumps(suggestions[:10]), 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    init_db_settings()
    app.run(debug=True)