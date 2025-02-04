function submitQuiz() {
    // Deshabilitar el botón de enviar y todos los inputs
    document.querySelector('button[type="button"]').disabled = true;
    document.querySelectorAll('.form-check-input').forEach(input => input.disabled = true);

    let questions = document.querySelectorAll('.form-check-input:checked');
    let answers = [];
    
    questions.forEach(input => {
        let questionText = input.closest('.mb-4').querySelector('h5').innerText;
        let selectedAnswer = input.value;
        
        answers.push({question: questionText, answer: selectedAnswer});
    });
    
    fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(answers)
    })
    .then(response => response.json())
    .then(data => {
        // Mostrar resultado total
        let resultContainer = document.getElementById('results');
        let score = (data.correct_count / data.results.length * 10).toFixed(1);
        resultContainer.innerHTML = `<div class='alert alert-info'><h4>Resultados</h4><p>Nota: ${score}/10 (${data.correct_count} de ${data.results.length} correctas)</p></div>`;
        
        // Mostrar feedback para cada pregunta
        data.results.forEach(res => {
                let questionDiv = Array.from(document.querySelectorAll('.mb-4')).find(div => 
                    div.dataset.question === res.question
                );
            
            let selectedInput = questionDiv.querySelector(`input[value="${res.selected_answer}"]`);
            let selectedDiv = selectedInput.closest('.d-flex');
            
            // Mostrar icono correcto/incorrecto
            if (res.is_correct) {
                selectedDiv.querySelector('.bi-check-circle-fill').style.display = 'inline';
            } else {
                selectedDiv.querySelector('.bi-x-circle-fill').style.display = 'inline';
                
                // Mostrar la respuesta correcta
                let correctAnswerDiv = Array.from(questionDiv.querySelectorAll('.d-flex')).find(div => 
                    div.querySelector('input').value === res.correct_answer
                );
                correctAnswerDiv.querySelector('.correct-answer').style.display = 'inline';
            }
        });
    });
}
