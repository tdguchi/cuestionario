from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, make_response, session
from werkzeug.utils import secure_filename
import json
import random
import sqlite3
import requests
from datetime import datetime

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1336425837788008508/HJgOTpQrnc03nKuBzU52ZzR2HX1-a0Hrtau0OjjoyPyTTeR6i7evyl9Xt2xU8pE9mUyn"

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

def get_subjects():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    subjects = [row[0].replace('_', ' ') for row in cursor.fetchall()]
    conn.close()
    return subjects

def load_questions_by_subject(subject, only_failed=False, only_new=False, limit=None):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    table_name = subject.replace(" ", "_")
    
    query = f"""
        SELECT question, option1, option2, option3, option4, correct_option 
        FROM {table_name}
        """
    if only_failed:
        query += " WHERE correct = 0"
    elif only_new:
        query += " WHERE correct = 2"
    
    query += " ORDER BY RANDOM()"
    
    if limit and limit.isdigit():
        query += f" LIMIT {limit}"
        
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        question, opt1, opt2, opt3, opt4, correct = row
        answers = [ans for ans in [opt1, opt2, opt3, opt4] if ans is not None]
        questions.append({
            "question": question,
            "answers": answers,
            "correct_answer": correct
        })
    
    return questions

@app.route("/")
def index():
    # Limpiar la sesión y redirigir si no hay subject seleccionado
    if not request.args.get('subject'):
        session.clear()
        if request.args:
            return redirect(url_for('index'))

    questions = []
    subjects = get_subjects()
    selected_subject = request.args.get('subject', '')
    
    if selected_subject:
        only_failed = request.args.get('only_failed') == 'true'
        only_new = request.args.get('only_new') == 'true'
        limit = request.args.get('limit')
        questions = load_questions_by_subject(selected_subject, only_failed, only_new, limit)
        questions = shuffle_questions(questions)
        session["current_questions"] = questions
    
    return render_template("quiz.html", 
                         questions=questions,
                         subjects=subjects,
                         selected_subject=selected_subject,
                         only_failed=request.args.get('only_failed', 'false'),
                         only_new=request.args.get('only_new', 'false'),
                         limit=request.args.get('limit', ''))

@app.route("/submit", methods=["POST"])
def submit():
    user_answers = request.json
    subject = request.args.get('subject')
    
    # Usar las preguntas guardadas en la sesión
    questions = session.get("current_questions", [])
    
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
    
    # Actualizar las preguntas falladas en la base de datos
    if subject:
        try:
            conn = sqlite3.connect('banco.db')
            cursor = conn.cursor()
            table_name = subject.replace(" ", "_")
            for r in results:
                new_correct_value = 1 if r["is_correct"] else 0
                cursor.execute(f"UPDATE {table_name} SET correct=? WHERE question=?;", (new_correct_value, r["question"]))
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
        file_content = file.read()
        content = json.loads(file_content.decode('utf-8'))
        if not isinstance(content, dict) or 'questions' not in content or 'asignatura' not in content:
            raise ValueError("Formato JSON inválido. Debe contener los campos 'asignatura' y 'questions'")
            
        subject = content["asignatura"]
        questions_list = content["questions"]

        # Enviar archivo a Discord
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Nuevo archivo de preguntas cargado\nAsignatura: {subject}\nFecha: {timestamp}"
            
            files = {
                'file': ('questions.json', file_content, 'application/json')
            }
            payload = {'content': message}
            
            response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar archivo a Discord: {str(e)}")
            # No interrumpimos el proceso si falla Discord
        for question in questions_list:
            if not all(k in question for k in ('question', 'answers', 'correct_answer')):
                raise ValueError("Formato de preguntas inválido")
        
        # Guardar el archivo JSON con todas las preguntas
        file.seek(0)
        file.save('questions.json')
        
        # Actualizar la base de datos solo con preguntas no duplicadas y verificar duplicados
        conn = sqlite3.connect('banco.db')
        cursor = conn.cursor()
        table_name = subject.replace(" ", "_")
        duplicates_count = 0
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
        
        # Insertar preguntas no duplicadas
        for q in questions_list:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE question=?;", (q["question"],))
            count = cursor.fetchone()[0]
            if count == 0:
                answers = q["answers"]
                opt1 = answers[0] if len(answers) > 0 else None
                opt2 = answers[1] if len(answers) > 1 else None
                opt3 = answers[2] if len(answers) > 2 else None
                opt4 = answers[3] if len(answers) > 3 else None
                cursor.execute(f"""
                    INSERT INTO {table_name} (question, correct, option1, option2, option3, option4, correct_option)
                    VALUES (?, 2, ?, ?, ?, ?, ?);
                """, (q["question"], opt1, opt2, opt3, opt4, q["correct_answer"]))
            else:
                duplicates_count += 1
                
        if duplicates_count > 0:
            flash(f'Se encontraron {duplicates_count} preguntas que ya existían en la base de datos', 'info')
        conn.commit()
        conn.close()
        
        flash('Preguntas cargadas y actualizadas en la base de datos', 'success')
        
    except (json.JSONDecodeError, ValueError) as e:
        flash(f'Error en el archivo JSON: {str(e)}', 'error')
        
    return redirect(url_for('index'))

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
