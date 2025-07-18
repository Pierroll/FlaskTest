from flask import Flask, render_template, request, jsonify, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_cambiala'

# Directorio para guardar los archivos JSON de tests
TESTS_DIR = 'tests'
if not os.path.exists(TESTS_DIR):
    os.makedirs(TESTS_DIR)

@app.route('/')
def index():
    """Página principal - mostrar tests disponibles"""
    tests = []
    if os.path.exists(TESTS_DIR):
        for filename in os.listdir(TESTS_DIR):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(TESTS_DIR, filename), 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        tests.append({
                            'filename': filename,
                            'title': test_data.get('title', filename.replace('.json', '')),
                            'description': test_data.get('description', 'Sin descripción'),
                            'questions_count': len(test_data.get('questions', []))
                        })
                except:
                    continue
    return render_template('index.html', tests=tests)

@app.route('/test/<filename>')
def take_test(filename):
    """Cargar y mostrar un test específico"""
    try:
        with open(os.path.join(TESTS_DIR, filename), 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Limpiar session anterior
        session.clear()
        session['test_filename'] = filename
        session['test_data'] = test_data
        session['user_answers'] = {}
        session['start_time'] = datetime.now().isoformat()
        
        return render_template('test.html', test=test_data, filename=filename)
    except FileNotFoundError:
        return "Test no encontrado", 404
    except json.JSONDecodeError:
        return "Error en el formato del test", 400

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Guardar respuesta del usuario"""
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if 'user_answers' not in session:
        session['user_answers'] = {}
    
    session['user_answers'][str(question_id)] = answer
    session.modified = True
    
    return jsonify({'status': 'success'})

@app.route('/finish_test', methods=['POST'])
def finish_test():
    """Finalizar test y calcular resultados"""
    if 'test_data' not in session or 'user_answers' not in session:
        return jsonify({'error': 'No hay test activo'}), 400
    
    test_data = session['test_data']
    user_answers = session['user_answers']
    
    results = {
        'total_questions': len(test_data['questions']),
        'answered_questions': len(user_answers),
        'correct_answers': 0,
        'incorrect_answers': 0,
        'details': []
    }
    
    for i, question in enumerate(test_data['questions']):
        question_id = str(i)
        user_answer = user_answers.get(question_id)
        correct_answer = question['correct_answer']
        
        is_correct = user_answer == correct_answer
        if is_correct:
            results['correct_answers'] += 1
        else:
            results['incorrect_answers'] += 1
        
        results['details'].append({
            'question': question['question'],
            'options': question['options'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
    
    # Calcular porcentaje
    if results['total_questions'] > 0:
        results['percentage'] = round((results['correct_answers'] / results['total_questions']) * 100, 2)
    else:
        results['percentage'] = 0
    
    session['test_results'] = results
    return jsonify(results)

@app.route('/results')
def show_results():
    """Mostrar página de resultados"""
    if 'test_results' not in session:
        return "No hay resultados disponibles", 404
    
    results = session['test_results']
    test_data = session.get('test_data', {})
    
    return render_template('results.html', results=results, test_title=test_data.get('title', 'Test'))

@app.route('/upload_test', methods=['GET', 'POST'])
def upload_test():
    """Subir un nuevo test en formato JSON"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    if 'test_file' not in request.files:
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    file = request.files['test_file']
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó archivo'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'El archivo debe ser formato JSON'}), 400
    
    try:
        # Validar estructura JSON
        content = file.read().decode('utf-8')
        test_data = json.loads(content)
        
        # Validar estructura requerida
        if 'questions' not in test_data:
            return jsonify({'error': 'El JSON debe contener una clave "questions"'}), 400
        
        for i, question in enumerate(test_data['questions']):
            required_fields = ['question', 'options', 'correct_answer']
            for field in required_fields:
                if field not in question:
                    return jsonify({'error': f'Pregunta {i+1}: falta el campo "{field}"'}), 400
        
        # Guardar archivo
        filename = file.filename
        filepath = os.path.join(TESTS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': 'Test subido correctamente'})
    
    except json.JSONDecodeError:
        return jsonify({'error': 'Formato JSON inválido'}), 400
    except Exception as e:
        return jsonify({'error': f'Error al procesar archivo: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)