// Make checkboxes mutually exclusive
document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            document.querySelectorAll('.filter-checkbox').forEach(other => {
                if (other !== this) other.checked = false;
            });
        }
    });
});

// Configuration section visibility
const setupConfigVisibility = () => {
    if (document.querySelector('#quiz-form')) {
        const configSection = document.querySelector('.config-section');
        const toggleButton = document.querySelector('.config-master-toggle');
        if (configSection && toggleButton) {
            configSection.style.display = 'none';
            toggleButton.querySelector('i').classList.remove('bi-chevron-up');
            toggleButton.querySelector('i').classList.add('bi-gear-fill');
        }
    }
};

// Master toggle for configuration sections
document.querySelector('.config-master-toggle')?.addEventListener('click', function() {
    const configSection = document.querySelector('.config-section');
    const icon = this.querySelector('i');
    
    if (configSection.style.display === 'none') {
        configSection.style.display = 'block';
        icon.classList.add('rotate');
    } else {
        configSection.style.display = 'none';
        icon.classList.remove('rotate');
    }
});

// Get all questions
const questions = Array.from(document.querySelectorAll('.mb-4[data-question]'));

// Allow selecting and deselecting answers
questions.forEach(question => {
    const inputs = question.querySelectorAll('.form-check-input');
    inputs.forEach(input => {
        let lastChecked = null;
        input.addEventListener('click', function(event) {
            if (this === lastChecked) {
                this.checked = false;
                lastChecked = null;
            } else {
                lastChecked = this;
            }
        });
    });
});

function submitQuiz() {
    // Get submit button and show loading state
    const submitBtn = document.querySelector('.submit-quiz');
    if (!submitBtn) return;

    // Disable submit button and show spinner
    submitBtn.disabled = true;
    submitBtn.querySelector('.loading-spinner').style.display = 'inline-block';

    // Get answers
    let answers = questions.map(div => ({
        question: div.querySelector('h5').innerText,
        answer: div.querySelector('.form-check-input:checked')?.value || null
    }));
    
    // Get current URL parameters and submit
    const urlParams = new URLSearchParams(window.location.search);
    const submitUrl = `/submit?${urlParams.toString()}`;
    
    fetch(submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(answers)
    })
    .then(response => response.json())
    .then(data => {
        if (!data.results) {
            throw new Error("Invalid response from server");
        }

        // Calculate values for display (no local grade calculation)
        const unansweredCount = data.results.filter(r => r.unanswered).length;
        const incorrectCount = data.results.length - data.correct_count - unansweredCount;

        // Create results card using final_score from the server
        const resultContainer = document.getElementById('results');
        resultContainer.innerHTML = `
            <div class='results-card fade-in'>
                <div class='results-summary'>
                    <div class='result-stat'>
                        <h5>${data.final_score}</h5>
                        <p>Nota final</p>
                    </div>
                    <div class='result-stat'>
                        <h5>${data.correct_count}</h5>
                        <p>Correctas</p>
                    </div>
                    <div class='result-stat'>
                        <h5>${incorrectCount}</h5>
                        <p>Incorrectas</p>
                    </div>
                    <div class='result-stat'>
                        <h5>${unansweredCount}</h5>
                        <p>Sin responder</p>
                    </div>
                </div>
            </div>
        `;

        // Process each question's result
        data.results.forEach(res => {
            const questionDiv = questions.find(div => 
                div.querySelector('h5').textContent.trim().replace(/\s+/g, ' ') === 
                res.question.trim().replace(/\s+/g, ' ')
            );

            if (!questionDiv) return;

            const answers = questionDiv.querySelectorAll('.d-flex');
            answers.forEach(answer => {
                const input = answer.querySelector('input[type="radio"]');
                if (!input) return;

                answer.classList.remove('correct', 'incorrect', 'unanswered-correct');

                if (res.unanswered && input.value === res.correct_answer) {
                    answer.classList.add('unanswered-correct');
                } else if (input.value === res.selected_answer) {
                    answer.classList.add(res.is_correct ? 'correct' : 'incorrect');
                } else if (input.value === res.correct_answer && !res.is_correct) {
                    answer.classList.add('correct');
                }
            });
        });

        // Scroll to results
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Hubo un error al procesar el cuestionario. Por favor, inténtalo de nuevo.');
    })
    .finally(() => {
        // Re-enable submit button and hide spinner
        submitBtn.disabled = false;
        submitBtn.querySelector('.loading-spinner').style.display = 'none';
    });
}

// Cargar configuración de puntuación
async function loadScoringConfig() {
    const response = await fetch('/api/scoring-config');
    const config = await response.json();
    
    document.getElementById('correct-value').value = config.correct_value;
    document.getElementById('incorrect-penalty').value = config.incorrect_penalty;
    document.getElementById('blank-penalty').value = config.blank_penalty;
    document.getElementById('base-score').value = config.base_score;
}

// Guardar configuración de puntuación
async function saveScoringConfig() {
    const config = {
        correct_value: parseFloat(document.getElementById('correct-value').value),
        incorrect_penalty: parseFloat(document.getElementById('incorrect-penalty').value),
        blank_penalty: parseFloat(document.getElementById('blank-penalty').value),
        base_score: parseFloat(document.getElementById('base-score').value)
    };

    await fetch('/api/scoring-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
}

// Añadir event listeners para guardar configuración
document.querySelectorAll('.scoring-config input').forEach(input => {
    input.addEventListener('change', saveScoringConfig);
});

// Cargar configuración al inicio
loadScoringConfig();

// Initialize config visibility on page load
setupConfigVisibility();