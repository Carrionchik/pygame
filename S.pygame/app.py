from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Функция для подключения к БД
def get_db():
    db = sqlite3.connect('database.db')
    db.row_factory = sqlite3.Row
    return db

# Инициализация БД (создание таблиц)
def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            max_wave INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    db.close()
    print("База данных инициализирована!")

# Главная страница - таблица лидеров
@app.route('/')
def index():
    db = get_db()
    # Получаем топ-10 игроков
    leaders = db.execute('''
        SELECT player_name, max_wave, score, created_at
        FROM leaderboard
        ORDER BY max_wave DESC, score DESC
        LIMIT 10
    ''').fetchall()
    db.close()
    
    return render_template('index.html', leaders=leaders)

# API: Отправить результат из игры
@app.route('/api/submit_score', methods=['POST'])
def submit_score():
    data = request.json
    player_name = data.get('player_name')
    max_wave = data.get('max_wave')
    score = data.get('score', 0)
    
    if not player_name or max_wave is None:
        return jsonify({'error': 'Неверные данные'}), 400
    
    db = get_db()
    db.execute(
        'INSERT INTO leaderboard (player_name, max_wave, score) VALUES (?, ?, ?)',
        (player_name, max_wave, score)
    )
    db.commit()
    db.close()
    
    return jsonify({'message': 'Результат сохранен!'}), 201

# API: Получить таблицу лидеров (для игры)
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    db = get_db()
    leaders = db.execute('''
        SELECT player_name, max_wave, score
        FROM leaderboard
        ORDER BY max_wave DESC, score DESC
        LIMIT 10
    ''').fetchall()
    db.close()
    
    return jsonify([dict(leader) for leader in leaders])

if __name__ == '__main__':
    init_db()
    print("Сервер запущен на http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)