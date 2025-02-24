from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import json
import random
import sqlite3
import requests
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(override=True)  # Forzar recarga de variables

# Debug de variables de entorno al inicio
webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
modo_coop = os.getenv('MODO_COOPERATIVO', 'false')

app = Flask(__name__)
app.secret_key = "secret_key"
DISCORD_WEBHOOK_URL = webhook_url
MODO_COOPERATIVO = modo_coop.lower() == 'true'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('banco.db')
    try:
        yield conn
    finally:
        conn.close()

def get_subjects() -> List[str]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [row[0].replace('_', ' ') for row in cursor.fetchall()]

def load_questions_by_subject(subject: str, only_failed: bool = False, only_new: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    table_name = subject.replace(" ", "_")
    query_parts = [
        f"SELECT question_id, question, option1, option2, option3, option4, correct_option FROM {table_name}"
    ]
    
    if only_failed:
        query_parts.append("WHERE correct = 0")
    elif only_new:
        query_parts.append("WHERE correct = 2")
    
    query_parts.append("ORDER BY RANDOM()")
    
    if limit and limit.isdigit():
        query_parts.append(f"LIMIT {limit}")  # Eliminar la restricción de máximo 24
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(" ".join(query_parts))
        rows = cursor.fetchall()
        
        return [{
            "question_id": row[0],
            "question": row[1],
            "answers": [ans for ans in row[2:6] if ans is not None],
            "correct_answer": row[6]
        } for row in rows]

def load_questions_by_ids(subject: str, question_ids: List[int]) -> List[Dict[str, Any]]:
    table_name = subject.replace(" ", "_")
    placeholders = ','.join('?' for _ in question_ids)
    query = f"SELECT question, option1, option2, option3, option4, correct_option FROM {table_name} WHERE question_id IN ({placeholders})"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, question_ids)
        rows = cursor.fetchall()
        
        return [{
            "question": row[0],
            "answers": [ans for ans in row[1:5] if ans is not None],
            "correct_answer": row[5]
        } for row in rows]

def should_preserve_order(answers: List[str]) -> bool:
    preserved_phrases = [
        "son correctas",
        "ninguna de las anteriores",
        "todas son correctas",
        "ninguna es correcta"
    ]
    return any(any(phrase in answer.lower() for phrase in preserved_phrases) for answer in answers)

def shuffle_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    random.shuffle(questions)
    for question in questions:
        if not should_preserve_order(question["answers"]):
            random.shuffle(question["answers"])
    return questions

@app.route("/")
def index():
    if not request.args.get('subject'):
        session.clear()
        if request.args:
            return redirect(url_for('index'))

    subjects = get_subjects()
    selected_subject = request.args.get('subject', '')
    questions = []
    
    if selected_subject:
        questions = load_questions_by_subject(
            selected_subject,
            only_failed=request.args.get('only_failed') == 'true',
            only_new=request.args.get('only_new') == 'true',
            limit=request.args.get('limit')
        )
        questions = shuffle_questions(questions)
        session["current_question_ids"] = [q["question_id"] for q in questions]
    
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
    question_ids = session.get("current_question_ids", [])
    
    if not question_ids:
        return jsonify({"error": "No hay preguntas para evaluar"}), 400
    if not user_answers:
        user_answers = []

    questions = load_questions_by_ids(subject, question_ids)
    results = []
    correct_count = 0
    answered_questions = {ua["question"]: ua["answer"] for ua in user_answers}

    for question in questions:
        question_text = question["question"]
        selected_answer = answered_questions.get(question_text, None)
        correct_answer = question["correct_answer"]
        
        is_correct = selected_answer == correct_answer if selected_answer is not None else False
        if is_correct:
            correct_count += 1

        results.append({
            "question": question_text,
            "selected_answer": selected_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "unanswered": selected_answer is None
        })

    # Eliminamos el cálculo antiguo basado en porcentaje:
    # score = round((correct_count / len(questions)) * 10, 1) if questions else 0

    if subject:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                table_name = subject.replace(" ", "_")
                cursor.executemany(
                    f"UPDATE {table_name} SET correct=? WHERE question=?",
                    [(1 if r["is_correct"] else 0, r["question"]) for r in results]
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error al actualizar la base de datos: {e}")
            return jsonify({"error": "Error al actualizar resultados"}), 500
    
    # Obtener configuración de puntuación para la asignatura
    scoring = get_scoring_config(subject)
    
    correct_count = sum(1 for r in results if r['is_correct'])
    incorrect_count = sum(1 for r in results if not r['is_correct'] and not r['unanswered'])
    blank_count = sum(1 for r in results if r['unanswered'])
    
    # Calcular nota final usando los valores de configuración
    final_score = (
        float(scoring['base_score']) +
        (correct_count * float(scoring['correct_value'])) -
        (incorrect_count * float(scoring['incorrect_penalty'])) -
        (blank_count * float(scoring['blank_penalty']))
    )
    
    # Asegurar que la nota está entre 0 y 10
    final_score = max(0, min(10, final_score))
    
    return jsonify({
        'results': results,
        'correct_count': correct_count,
        'final_score': final_score
    })

@app.route("/upload", methods=["POST"])
def upload_file():
    
    if 'file' not in request.files or not request.files['file'].filename:
        flash('No se ha seleccionado ningún archivo', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
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

        # Enviar archivo a Discord solo si modo_cooperativo está activado
        if MODO_COOPERATIVO and DISCORD_WEBHOOK_URL:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Nuevo archivo de preguntas cargado\nAsignatura: {subject}\nFecha: {timestamp}"
                response = requests.post(
                    DISCORD_WEBHOOK_URL,
                    data={'content': message},
                    files={'file': ('questions.json', file_content, 'application/json')}
                )

            except requests.exceptions.RequestException as e:
                print(f"Error al enviar archivo a Discord: {e}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            table_name = subject.replace(" ", "_")
            
            # Crear tabla si no existe
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
            duplicates_count = 0
            for q in questions_list:
                if not all(k in q for k in ('question', 'answers', 'correct_answer')):
                    raise ValueError("Formato de preguntas inválido")
                    
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE question=?", (q["question"],))
                if cursor.fetchone()[0] == 0:
                    answers = q["answers"]
                    cursor.execute(
                        f"INSERT INTO {table_name} (question, correct, option1, option2, option3, option4, correct_option) "
                        "VALUES (?, 2, ?, ?, ?, ?, ?)",
                        (
                            q["question"],
                            answers[0] if len(answers) > 0 else None,
                            answers[1] if len(answers) > 1 else None,
                            answers[2] if len(answers) > 2 else None,
                            answers[3] if len(answers) > 3 else None,
                            q["correct_answer"]
                        )
                    )
                else:
                    duplicates_count += 1
            
            conn.commit()
        
        if duplicates_count > 0:
            flash(f'Se encontraron {duplicates_count} preguntas que ya existían en la base de datos', 'info')
        flash('Preguntas cargadas y actualizadas en la base de datos', 'success')
        
    except (json.JSONDecodeError, ValueError) as e:
        flash(f'Error en el archivo JSON: {str(e)}', 'error')
    except sqlite3.Error as e:
        flash(f'Error en la base de datos: {str(e)}', 'error')
    
    return redirect(url_for('index'))

def get_scoring_config(subject=None):
    """Obtiene la configuración de puntuación para una asignatura específica o la global"""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        if subject:
            cursor = conn.execute(
                'SELECT * FROM scoring_config WHERE subject = ?',
                (subject,)
            )
        else:
            cursor = conn.execute(
                'SELECT * FROM scoring_config WHERE subject IS NULL'
            )
        config = cursor.fetchone()
        
        # Si no hay configuración específica, usar la global
        if not config:
            cursor = conn.execute(
                'SELECT * FROM scoring_config WHERE subject IS NULL'
            )
            config = cursor.fetchone()
            
        return config

@app.route('/api/scoring-config', methods=['GET'])
def api_get_scoring_config():
    subject = request.args.get('subject')
    config = get_scoring_config(subject)
    return jsonify({
        'correct_value': float(config['correct_value']),
        'incorrect_penalty': float(config['incorrect_penalty']),
        'blank_penalty': float(config['blank_penalty']),
        'base_score': float(config['base_score'])
    })

@app.route('/api/scoring-config', methods=['POST'])
def update_scoring_config():
    config = request.get_json()
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE scoring_config 
            SET correct_value = ?, incorrect_penalty = ?, 
                blank_penalty = ?, base_score = ?
            WHERE id = 1
        ''', (
            config['correct_value'],
            config['incorrect_penalty'],
            config['blank_penalty'],
            config['base_score']
        ))
        conn.commit()
        return jsonify({'status': 'success'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
