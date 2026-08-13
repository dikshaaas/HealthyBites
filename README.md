# 🥗 HealthyBites

> **An Ingredient-Based Recipe Recommendation System with AI-Powered Fallback Generation**
>
> Final Year Project — Built with Flask, MySQL, TF-IDF, and a custom Trigram Language Model

---

## 📌 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Core Algorithms](#core-algorithms)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [Admin Panel](#admin-panel)
- [Screenshots](#screenshots)

---

## Overview

**HealthyBites** is a web application that helps users discover recipes based on ingredients they already have at home. Instead of browsing endless cookbooks or shopping for specific items, users simply enter their available ingredients and the system retrieves the best matching recipes using a multi-stage retrieval pipeline.

When no database matches are found, a built-in **AI Recipe Generator** using a **Trigram Language Model** creates a new recipe on-the-fly from the user's ingredients — complete with structured cooking steps, calorie estimates, and prep time.

---

## Features

### 👤 User Features
- **Ingredient-based Search** — Enter available ingredients with optional meal type (Breakfast / Lunch / Dinner) and allergy filters
- **Strict Match** — Recipes where all core ingredients match exactly what you have
- **Partial Match** — Recipes that closely match using TF-IDF cosine similarity scoring
- **Healthy Alternative Suggestions** — Automatically surfaces a lower-calorie alternative alongside the main match
- **AI Recipe Generation** — Trigram-model-based recipe creation when no database match is found ("Magic Generate")
- **Recipe Detail Pages** — Full ingredient lists and step-by-step cooking instructions
- **Save / Unsave Recipes** — Bookmark favourite recipes to your personal collection
- **Recipe History** — Tracks your recently viewed recipes
- **User Profile** — Update username, email, profile picture, and change password
- **Allergy Filtering** — Exclude recipes containing specified allergens

### 🛡️ Admin Features
- **Admin Dashboard** — Overview statistics with visual charts (total users, total recipes, saved recipes)
- **User Management** — View, promote/demote, and delete users
- **Recipe Management** — Browse, add, edit, and delete recipes from the database
- **AI-Generated Recipe Review** — Approve or reject AI-generated recipes submitted by users
- **Site Settings** — Customise the homepage hero title, subtitle, tags, and theme colours

---

## System Architecture

```
User Input (Ingredients + Meal Type + Allergies)
          │
          ▼
┌─────────────────────────┐
│   Preprocessing Layer   │  ← Normalise ingredients
└──────────┬──────────────┘
           │
     ┌─────▼──────┐
     │ Strict Match│  ← Exact ingredient-set matching
     └─────┬───────┘
           │ No results?
     ┌─────▼──────┐
     │Partial Match│  ← TF-IDF cosine similarity
     └─────┬───────┘
           │ No results?
     ┌─────▼────────────────┐
     │ AI Recipe Generator  │  ← Trigram Language Model
     │ (HybridRecipeGenerator)│
     └──────────────────────┘
           │
     ┌─────▼────────────────────┐
     │ Incompatibility Filter   │  ← Remove unsafe combos
     │ Allergy Filter           │
     │ Ranking Engine           │  ← Meal-type aware ranking
     └──────────────────────────┘
           │
     Results / Generated Recipe
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | Flask (Python) |
| **Database** | MySQL via `mysql-connector-python` |
| **ORM / Query Layer** | Raw SQL with `mysql.connector` |
| **Data Processing** | Pandas |
| **Authentication** | Werkzeug (password hashing + session management) |
| **Frontend** | HTML5, CSS3, JavaScript (Jinja2 templates) |
| **File Uploads** | Werkzeug `secure_filename` |

---

## Core Algorithms

### 1. TF-IDF Cosine Similarity (`core/tfidf_algorithm.py`)
Used for **partial matching** — measures how similar a user's ingredient list is to each recipe's ingredient set.

- **IDF Calculation**: `log((N+1) / (df+1)) + 1` — down-weights common ingredients
- **Sparse Vector Representation**: Memory-efficient ingredient vectors
- **Cosine Similarity**: Angle-based similarity scoring independent of ingredient count

### 2. Strict Match Engine (`core/strict_match_engine.py`)
Finds recipes where all of the recipe's **core ingredients** are present in the user's ingredient list. Supports a configurable tolerance for extra core ingredients.

### 3. Partial Match Engine (`core/partial_match_engine.py`)
Falls back to TF-IDF similarity when no strict match exists. Returns recipes above a configurable similarity threshold (default: `0.15`).

### 4. Ranking Engine (`core/ranking_engine.py`)
Applies **meal-type-aware ranking** to the matched results:

| Meal Type | Ranking Strategy |
|-----------|-----------------|
| Breakfast | Filter ≤20 min, then sort by time ↑ and calories ↑ |
| Lunch | Sort by calories ↓ (more filling) |
| Dinner | Sort by calories ↑ and time ↑ |

### 5. Trigram Language Model — AI Recipe Generator (`core/generation_engine.py`)
The `HybridRecipeGenerator` creates original recipes when the database has no matches:

- **Training**: Builds a trigram model from all recipe instruction texts in the database at startup
- **Ingredient Validation**: Validates user inputs against a learned vocabulary; rejects non-food items
- **Incompatibility Detection**: Blocks known incompatible pairings (e.g., fish + chocolate)
- **Ingredient Augmentation**: Automatically adds contextually appropriate pantry items (e.g., chicken → garlic, thyme, olive oil)
- **Hallucination Prevention**: Filters the trigram's next-word predictions to only allow validated ingredient words
- **Step Generation**: Produces structured cooking steps (Preparation → Heating → Cooking → Serving)
- **Metadata Estimation**: Estimates calories and prep time from ingredient count and complexity

### 6. Incompatibility Engine (`core/incompatibility_engine.py`)
Filters out recipes containing known dangerous or unpalatable ingredient combinations before presenting results to the user.

---

## Project Structure

```
HealthyBites/
│
├── app.py                        # Main Flask application & all route handlers
├── db_config.py                  # MySQL database connection configuration
├── migrate_recipes.py            # Database migration utility script
│
├── core/                         # Core recommendation engine modules
│   ├── generation_engine.py      # HybridRecipeGenerator (Trigram AI model)
│   ├── retrieval_engine.py       # Main retrieval pipeline orchestrator
│   ├── strict_match_engine.py    # Exact ingredient set matching
│   ├── partial_match_engine.py   # TF-IDF based partial matching
│   ├── ranking_engine.py         # Meal-type-aware result ranking
│   ├── tfidf_algorithm.py        # TF-IDF & cosine similarity implementation
│   ├── incompatibility_engine.py # Ingredient compatibility filtering
│   └── preprocessing.py          # Ingredient normalisation utilities
│
├── templates/                    # Jinja2 HTML templates
│   ├── base.html                 # Base layout template
│   ├── home.html                 # Landing page
│   ├── search.html               # Ingredient search form
│   ├── choose_recipe.html        # Search results & recipe selection
│   ├── recipe_detail.html        # Standard recipe detail page
│   ├── ai_recipe_detail.html     # AI-generated recipe detail page
│   ├── recipe_alternative_detail.html  # Healthy alternative detail
│   ├── partial_results.html      # Partial match results listing
│   ├── dashboard.html            # User dashboard (saved & viewed)
│   ├── profile.html              # User profile management
│   ├── login.html                # Login page
│   ├── register.html             # Registration page
│   ├── about.html                # About us page
│   └── admin/                    # Admin panel templates
│
├── static/                       # Static assets
│   ├── css/                      # Stylesheets
│   ├── js/                       # JavaScript files
│   ├── images/                   # Static images
│   └── uploads/profiles/         # User profile picture uploads
│
├── data/                         # Dataset files
│   ├── raw/                      # Original raw dataset
│   ├── processed/                # Cleaned & processed data
│   ├── sample/                   # Sample data subsets
│   └── sampled/                  # Sampled subsets for testing
│
├── scripts/                      # Utility scripts
│   ├── clean_dataset.py          # Dataset cleaning script
│   └── inspect_schema.py         # Database schema inspection
│
├── notebook/                     # Jupyter notebooks (EDA, model experiments)
│
└── healthybites/                 # Python virtual environment
```

---

## Database Schema

The application uses a **MySQL** database named `healthybites` with the following core tables:

| Table | Description |
|-------|-------------|
| `users` | User accounts (id, username, email, password_hash, role, profile_image) |
| `recipes` | Recipe database (name, core_ingredients JSON, pantry_ingredients JSON, instructions JSON, calories, minutes) |
| `saved_recipes` | User-saved/bookmarked recipes (user_id, recipe_name) |
| `viewed_recipes` | User recipe view history (user_id, recipe_name) |
| `generated_recipes` | AI-generated recipe history per user (title, ingredients, steps, source, is_approved) |
| `site_settings` | Admin-configurable homepage content and theme settings |

---

## Setup & Installation

### Prerequisites
- Python 3.8+
- MySQL Server (running locally)
- pip

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/HealthyBites.git
cd HealthyBites
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install flask mysql-connector-python pandas werkzeug
```

### 4. Configure the Database

Start MySQL and create the database:
```sql
CREATE DATABASE healthybites;
```

Update `db_config.py` with your MySQL credentials:
```python
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="your_username",      # Change this
        password="your_password",  # Change this
        database="healthybites"
    )
```

### 5. Import Recipe Data
```bash
python migrate_recipes.py
```

### 6. Create an Admin User

After running the app once (so tables auto-create), manually set a user's role to admin in MySQL:
```sql
UPDATE users SET role = 'admin' WHERE username = 'your_username';
```

---

## Running the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

> **Note:** On first startup, the engine will train the Trigram model from the recipe database. This may take a few seconds depending on the dataset size.

---

## Usage Guide

### Finding a Recipe
1. **Register / Login** to your account
2. Navigate to **Search**
3. Enter your available ingredients (comma-separated): e.g., `chicken, garlic, onion`
4. Select a **meal type**: Breakfast, Lunch, or Dinner
5. Optionally enter any **allergies**: e.g., `peanuts, shellfish`
6. Click **Find Recipes**

### Understanding Results
| Result Type | Meaning |
|-------------|---------|
| ✅ **Strict Match** | All recipe core ingredients are available in your kitchen |
| 🔶 **Partial Match** | Most ingredients match; you may need 1–2 extras |
| 🤖 **AI Generated** | No database match found; a custom recipe was generated using AI |

### When No Recipes Are Found
If the database has no matches, you'll see a **"Generate with AI"** button. Click it to have the Trigram AI model create a brand-new recipe using your ingredients.

---

## Admin Panel

Access the admin panel at `/admin/dashboard` after logging in with an admin account.

### Admin Capabilities
- 📊 **Dashboard** — View user counts, recipe counts, and charts
- 👥 **Manage Users** — View all users, change roles, delete accounts
- 🍽️ **Manage Recipes** — Add/edit/delete recipes in the database
- 🤖 **AI Recipe Review** — Approve or reject user-generated AI recipes
- ⚙️ **Site Settings** — Edit homepage hero content and theme colour scheme

---
## Screenshots
<img width="2846" height="1485" alt="image" src="https://github.com/user-attachments/assets/4d74bc0b-0bfd-41c9-b011-992257299db1" />
<img width="2844" height="1104" alt="image" src="https://github.com/user-attachments/assets/c010e088-6992-402b-9512-f5d6a39c983c" />
<img width="2106" height="1512" alt="image" src="https://github.com/user-attachments/assets/1ba5cdcd-1457-4d9c-bb87-73a2c294f0f4" />
<img width="2222" height="1484" alt="image" src="https://github.com/user-attachments/assets/3ba5cf9f-32b3-4d45-9c8f-3e52d8975880" />
<img width="2082" height="1524" alt="image" src="https://github.com/user-attachments/assets/d68f4c73-48c0-44aa-b361-d8115489b321" />
<img width="2231" height="1516" alt="image" src="https://github.com/user-attachments/assets/8312992d-e404-42c1-90dd-1d44783cb522" />
<img width="2836" height="1527" alt="image" src="https://github.com/user-attachments/assets/1381d02e-e09d-42f7-9731-698e76f30568" />
<img width="2024" height="1500" alt="image" src="https://github.com/user-attachments/assets/a2f0dcf6-7094-4e02-81ef-4546d6850324" />


## Acknowledgements

- Recipe dataset sourced and processed for academic use
- Built as a Final Year Project demonstrating NLP-based information retrieval techniques
- Trigram language model inspired by classical N-gram statistical language modelling

---

*HealthyBites — Cook great meals with what you already have.*
