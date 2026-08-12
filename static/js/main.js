// ============================================================
//  HealthyBites - Main JavaScript
//  File: static/js/main.js
//  Linked from: base.html (All pages)
// ============================================================

document.addEventListener('DOMContentLoaded', function () {

    // ── Flash message auto-hide ──────────────────────────── 
    // (Triggered by session flashes in base.html)
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity 0.4s ease';
            msg.style.opacity = '0';
            setTimeout(function () { msg.remove(); }, 400);
        }, 4500);
    });

    // ── Trending recipe carousel scroll ─────────────────── 
    // (Used in home.html - Currently hidden as per user simplicity request)
    const wrapper = document.getElementById('trendingWrapper');
    const btnPrev = document.getElementById('trendingPrev');
    const btnNext = document.getElementById('trendingNext');

    if (wrapper && btnPrev && btnNext) {
        const scrollAmount = 260;
        btnNext.addEventListener('click', function () {
            wrapper.scrollBy({ left: scrollAmount, behavior: 'smooth' });
        });
        btnPrev.addEventListener('click', function () {
            wrapper.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
        });
    }

    // ── Quick suggest tags (home page) ──────────────────── 
    // (Used in home.html hero section search form)
    const heroInput = document.getElementById('heroIngredientInput');
    const heroTags = document.querySelectorAll('.hero-tag');

    if (heroInput) {
        heroTags.forEach(function (tag) {
            tag.addEventListener('click', function () {
                const ingredient = this.dataset.ingredient;
                const current = heroInput.value.trim();
                heroInput.value = current
                    ? current + ', ' + ingredient
                    : ingredient;
                heroInput.focus();
            });
        });
    }

    // ── Interactive recipe detail flow ──────────────────────
    // (Used in recipe_detail.html and recipe_alternative_detail.html)
    const interactiveRecipe = document.querySelector('.interactive-recipe');
    if (interactiveRecipe) {
        const ingredientChecks = interactiveRecipe.querySelectorAll('[data-role="ingredient"]');
        const stepButtons = interactiveRecipe.querySelectorAll('[data-role="step"]');
        const progressText = interactiveRecipe.querySelector('.ingredient-progress-text');
        const stepsWrap = interactiveRecipe.querySelector('#interactiveStepsWrap');
        const completeBanner = interactiveRecipe.querySelector('#cookingCompleteBanner');

        const updateIngredientProgress = function () {
            const checkedCount = interactiveRecipe.querySelectorAll('[data-role="ingredient"]:checked').length;
            const totalCount = ingredientChecks.length;

            if (progressText) {
                progressText.textContent = checkedCount + ' / ' + totalCount + ' selected';
            }

            if (!stepsWrap) return;
            const hasAllIngredients = totalCount > 0 && checkedCount === totalCount;
            stepsWrap.classList.toggle('is-locked', !hasAllIngredients);
            if (!hasAllIngredients && completeBanner) {
                completeBanner.classList.remove('is-visible');
            }
        };

        ingredientChecks.forEach(function (checkbox) {
            checkbox.addEventListener('change', updateIngredientProgress);
        });

        stepButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (stepsWrap && stepsWrap.classList.contains('is-locked')) {
                    return;
                }

                btn.classList.toggle('is-done');
                const allDone = Array.from(stepButtons).every(function (item) {
                    return item.classList.contains('is-done');
                });

                if (completeBanner) {
                    completeBanner.classList.toggle('is-visible', allDone);
                }
            });
        });

        updateIngredientProgress();
    }

    // Backward-compatible healthy section toggle (results page)
    window.toggleHealthy = function () {
        const section = document.getElementById('healthySection');
        const btn = document.getElementById('healthyToggleBtn');
        if (!section) return;
        const isHidden = section.style.display === 'none' || section.style.display === '';
        section.style.display = isHidden ? 'block' : 'none';
        if (btn) {
            btn.textContent = isHidden
                ? 'Hide Healthier Alternative'
                : 'Show Healthier Alternative';
        }
    };

    const healthySection = document.getElementById('healthySection');
    if (healthySection && !document.querySelector('.interactive-recipe')) {
        healthySection.style.display = 'none';
    }

});
