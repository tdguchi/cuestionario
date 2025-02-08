// Make checkboxes mutually exclusive
document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            // Uncheck other checkboxes
            document.querySelectorAll('.filter-checkbox').forEach(other => {
                if (other !== this) {
                    other.checked = false;
                }
            });
        }
    });
});

// Auto-hide config sections if questions are present
if (document.querySelector('#quiz-form')) {
    const configSection = document.querySelector('.config-section');
    const toggleButton = document.querySelector('.config-master-toggle');
    if (configSection && toggleButton) {
        configSection.style.display = 'none';
        toggleButton.querySelector('i').classList.remove('bi-chevron-up');
        toggleButton.querySelector('i').classList.add('bi-gear-fill');
    }
}

// Master toggle for configuration sections
document.querySelector('.config-master-toggle').addEventListener('click', function() {
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

function submitQuiz() {
    // Disable submit button
    document.querySelector('button[onclick="submitQuiz()"]').disabled = true;

    // Get all questions
    let questionDivs = document.querySelectorAll('.mb-4');
    let answers = [];
    
    questionDivs.forEach(div => {
        let questionTextElement = div.querySelector('h5');
        if (!questionTextElement) {
            console.error('Could not find question text element in:', div);
            return;
        }
        let questionText = questionTextElement.innerText;
        let selectedInput = div.querySelector('.form-check-input:checked');
        let selectedAnswer = selectedInput ? selectedInput.value : null;
        console.log('Submitting question:', questionText);
        console.log('Selected answer:', selectedAnswer);
        answers.push({
            question: questionText, 
            answer: selectedAnswer
        });
    });
    
    // Get current URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const submitUrl = `/submit?${urlParams.toString()}`;
    console.log('Submitting to:', submitUrl);
    console.log('Answers:', answers);
    
    fetch(submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(answers)
    })
    .then(response => response.json())
    .then(data => {
        // Show total result
        let resultContainer = document.getElementById('results');
        let score = (data.correct_count / data.results.length * 10).toFixed(1);
        resultContainer.innerHTML = `<div class='alert alert-info'><h4>Resultados</h4><p>Nota: ${score}/10 (${data.correct_count} de ${data.results.length} correctas)</p></div>`;
        
        data.results.forEach(res => {
            console.log('Processing result for question:', JSON.stringify(res.question));

            // Find question by exact text match (clean up whitespace)
            const questionDiv = Array.from(document.querySelectorAll('.mb-4')).find(div => {
                const questionText = div.querySelector('h5')?.textContent?.trim().replace(/\s+/g, ' ') || '';
                const resQuestion = res.question.trim().replace(/\s+/g, ' ');
                console.log('Comparing:', JSON.stringify(questionText), 'with', JSON.stringify(resQuestion));
                return questionText === resQuestion;
            });

            if (!questionDiv) {
                console.error('Could not find question div for:', res.question);
                return;
            }

            console.log('Found question div:', questionDiv.outerHTML);

            // Get answer container and answers
            const answerContainer = questionDiv.querySelector('.form-check.answer-container');
            if (!answerContainer) {
                console.error('Could not find answer container');
                return;
            }

            // Remove previous results
            const answers = answerContainer.querySelectorAll('.d-flex');
            answers.forEach(answer => {
                answer.classList.remove('correct', 'incorrect', 'unanswered-correct');
            });

            // Process each answer
            answers.forEach(answerDiv => {
                const input = answerDiv.querySelector('input[type="radio"]');
                if (!input) {
                    console.log('No input found in:', answerDiv.outerHTML);
                    return;
                }

                const label = answerDiv.querySelector('label');
                console.log('Processing answer:', {
                    value: input.value,
                    text: label?.textContent?.trim(),
                    selected: input.value === res.selected_answer,
                    correct: input.value === res.correct_answer,
                    unanswered: res.unanswered
                });

                if (res.unanswered && input.value === res.correct_answer) {
                    // Highlight correct answer in blue for unanswered questions
                    answerDiv.classList.add('unanswered-correct');
                } else if (input.value === res.selected_answer) {
                    if (res.is_correct) {
                        answerDiv.classList.add('correct');
                    } else {
                        answerDiv.classList.add('incorrect');
                    }
                } else if (input.value === res.correct_answer && !res.is_correct) {
                    answerDiv.classList.add('correct');
                }
            });
        });
    });
}
