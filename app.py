from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, make_response, session
from werkzeug.utils import secure_filename
import json
import random
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Necesario para flash messages

# Cargar preguntas desde un archivo JSON
def load_questions():
    with open("questions.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data["questions"]

# FunciÃ³n para mezclar preguntas y respuestas
def shuffle_questions(questions):
    random.shuffle(questions)
    for question in questions:
        random.shuffle(question["answers"])
    return questions

@app.route("/")
def index():
    questions = load_questions()
    shuffled_questions = shuffle_questions(questions)
    return render_template("quiz.html", questions=shuffled_questions)

@app.route("/submit", methods=["POST"])
def submit():
    user_answers = request.json
    questions = load_questions()
    correct_count = 0
    results = []

    for user_answer in user_answers:
        question_text = user_answer["question"]
        selected_answer = user_answer["answer"]
        correct_answer = next(q for q in questions if q["question"] == question_text)["correct_answer"]
        is_correct = selected_answer == correct_answer
        if is_correct:
            correct_count += 1
        results.append({
            "question": question_text,
            "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        })

    score = round((correct_count / len(questions)) * 10, 1) if questions else 0
    session["failed_questions"] = [r for r in results if not r["is_correct"]]
    
    # Actualizar las preguntas falladas en la base de datos: marcar como 0
    try:
        with open("questions.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        subject = data.get("asignatura")
        if subject:
            conn = sqlite3.connect('banco.db')
            cursor = conn.cursor()
            table_name = subject.replace(" ", "_")
            for r in results:
                if not r["is_correct"]:
                    cursor.execute(f"UPDATE {table_name} SET correct=0 WHERE question=?;", (r["question"],))
            conn.commit()
            conn.close()
    except Exception as e:
        print("Error al actualizar la base de datos:", e)
    
    return jsonify({"correct_count": correct_count, "nota": score, "results": results})

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        flash('No se ha seleccionado ningún archivo', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No se ha seleccionado ningún archivo', 'error')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.json'):
        flash('El archivo debe ser un JSON', 'error')
        return redirect(url_for('index'))
    
    try:
        content = json.loads(file.read().decode('utf-8'))
        if not isinstance(content, dict) or 'questions' not in content or 'asignatura' not in content:
            raise ValueError("Formato JSON inválido. Debe contener los campos 'asignatura' y 'questions'")
            
        subject = content["asignatura"]
        questions_list = content["questions"]
        for question in questions_list:
            if not all(k in question for k in ('question', 'answers', 'correct_answer')):
                raise ValueError("Formato de preguntas inválido")
            
        file.seek(0)
        file.save('questions.json')
        
        # Actualizar la base de datos
        conn = sqlite3.connect('banco.db')
        cursor = conn.cursor()
        table_name = subject.replace(" ", "_")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    correct BOOLEAN NOT NULL,
                    option1 TEXT,
                    option2 TEXT,
                    option3 TEXT,
                    option4 TEXT,
                    correct_option TEXT
                );
            """)
        for q in questions_list:
            q_text = q["question"]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE question=?;", (q_text,))
            count = cursor.fetchone()[0]
            if count == 0:
                answers = q["answers"]
                opt1 = answers[0] if len(answers) > 0 else None
                opt2 = answers[1] if len(answers) > 1 else None
                opt3 = answers[2] if len(answers) > 2 else None
                opt4 = answers[3] if len(answers) > 3 else None
                cursor.execute(f"""
                    INSERT INTO {table_name} (question, correct, option1, option2, option3, option4, correct_option)
                    VALUES (?, 1, ?, ?, ?, ?, ?);
                """, (q_text, opt1, opt2, opt3, opt4, q["correct_answer"]))
        conn.commit()
        conn.close()
        
        flash('Preguntas cargadas y actualizadas en la base de datos', 'success')
        
    except (json.JSONDecodeError, ValueError) as e:
        flash(f'Error en el archivo JSON: {str(e)}', 'error')
        
    return redirect(url_for('index'))

@app.route("/download")
def download():
    failed = session.get("failed_questions", [])
    response = jsonify({"failed_questions": failed})
    response.headers["Content-Disposition"] = "attachment; filename=failed_questions.json"
    return response

def init_db():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    subjects = ['Matematicas', 'Historia', 'Ciencia']
    for subject in subjects:
        table_name = subject.replace(" ", "_")
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                correct BOOLEAN NOT NULL,
                option1 TEXT,
                option2 TEXT,
                option3 TEXT,
                option4 TEXT,
                correct_option TEXT
            );
        """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
