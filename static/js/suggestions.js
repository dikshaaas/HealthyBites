/**
 * Ingredient Autocomplete / Suggestions
 */
document.addEventListener('DOMContentLoaded', () => {
    const ingredientInput = document.getElementById('ingredientInput');
    const suggestionBox = document.getElementById('suggestionBox');
    
    if (!ingredientInput || !suggestionBox) return;

    let debounceTimer;

    ingredientInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const value = e.target.value;
        const lastPart = value.split(',').pop().trim();

        if (lastPart.length < 1) {
            suggestionBox.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/ingredients?q=${encodeURIComponent(lastPart)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.length > 0) {
                        renderSuggestions(data, lastPart);
                    } else {
                        suggestionBox.style.display = 'none';
                    }
                })
                .catch(err => console.error('Suggestion error:', err));
        }, 200);
    });

    function renderSuggestions(suggestions, currentPart) {
        suggestionBox.innerHTML = '';
        suggestions.forEach(item => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.textContent = item;
            div.addEventListener('click', () => {
                applySuggestion(item);
            });
            suggestionBox.appendChild(div);
        });
        suggestionBox.style.display = 'block';
    }

    function applySuggestion(suggestion) {
        const parts = ingredientInput.value.split(',');
        parts.pop(); // Remove the partial string
        parts.push(suggestion);
        ingredientInput.value = parts.join(', ') + ', ';
        suggestionBox.style.display = 'none';
        ingredientInput.focus();
    }

    // Hide suggestions on outside click
    document.addEventListener('click', (e) => {
        if (!suggestionBox.contains(e.target) && e.target !== ingredientInput) {
            suggestionBox.style.display = 'none';
        }
    });
});
