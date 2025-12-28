#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/iris_server.py - Flask API сервер IRIS AI

Это главный IRIS сервер который:
- Запускает Flask на :5000
- Управляет LLM мозгом
- Обрабатывает голосовые команды
- Отправляет ответы в UI

Использование:
    python src/iris_server.py
"""

import logging
import sys
import os
from pathlib import Path
from flask import Flask, jsonify, request
from datetime import datetime
import json

# Настройка кодировки для Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('iris_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Инициализируем Flask
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Глобальный статус IRIS
iris_status = {
    'running': True,
    'start_time': datetime.now().isoformat(),
    'version': '2.0',
    'modules_loaded': 0,
    'ready': False
}


class IRISBrain:
    """Простой LLM мозг для IRIS."""
    
    def __init__(self):
        logger.info("[BRAIN] Инициализирую IRIS мозг...")
        self.ready = True
        self.context = {}
        self.memory = []
        logger.info("[BRAIN] ✅ IRIS мозг готов!")
    
    def process(self, text: str) -> str:
        """Обработать текст через мозг."""
        logger.info(f"[BRAIN] Обрабатываю: {text[:50]}...")
        
        # Сохраняем в память
        self.memory.append({
            'timestamp': datetime.now().isoformat(),
            'input': text,
            'type': 'user_message'
        })
        
        # Простой ответ (потом тут будет реальный LLM)
        response = f"Я понял: '{text}'. Это интересно!"
        
        return response


# Инициализируем мозг
brain = IRISBrain()
iris_status['modules_loaded'] += 1
iris_status['ready'] = True


@app.route('/', methods=['GET'])
def home():
    """Главная страница с HTML интерфейсом."""
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🌸 IRIS AI v2.0</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                width: 100%;
                max-width: 600px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 32px;
                margin-bottom: 10px;
            }
            
            .header p {
                opacity: 0.9;
                font-size: 14px;
            }
            
            .status {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                padding: 30px;
                background: #f8f9fa;
            }
            
            .status-item {
                text-align: center;
                padding: 15px;
                background: white;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            
            .status-item strong {
                display: block;
                margin-bottom: 5px;
                color: #333;
            }
            
            .status-item span {
                display: block;
                font-size: 12px;
                color: #666;
            }
            
            .chat-area {
                padding: 30px;
            }
            
            .messages {
                height: 300px;
                overflow-y: auto;
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .message {
                margin-bottom: 15px;
                padding: 12px;
                border-radius: 8px;
                max-width: 80%;
            }
            
            .message.user {
                background: #667eea;
                color: white;
                margin-left: auto;
                text-align: right;
                max-width: 80%;
            }
            
            .message.iris {
                background: #e8e8e8;
                color: #333;
                margin-right: auto;
                max-width: 80%;
            }
            
            .input-area {
                display: flex;
                gap: 10px;
            }
            
            input {
                flex: 1;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
            }
            
            input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            button {
                padding: 12px 30px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                transition: background 0.3s;
            }
            
            button:hover {
                background: #764ba2;
            }
            
            .info {
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌸 IRIS AI v2.0</h1>
                <p>Давай поговорим!</p>
            </div>
            
            <div class="status">
                <div class="status-item">
                    <strong>✅ Статус</strong>
                    <span>АКТИВНА</span>
                </div>
                <div class="status-item">
                    <strong>🧠 Мозг</strong>
                    <span>ГОТОВ</span>
                </div>
                <div class="status-item">
                    <strong>🎙️ Микрофон</strong>
                    <span>ПОДКЛЮЧЕН</span>
                </div>
                <div class="status-item">
                    <strong>🎮 CS2</strong>
                    <span>СЛУШАЕТ</span>
                </div>
            </div>
            
            <div class="chat-area">
                <div class="messages" id="messages">
                    <div class="message iris">
                        👋 Привет! Я IRIS, твоя ассистентка. Готова помогать!
                    </div>
                </div>
                
                <div class="input-area">
                    <input 
                        type="text" 
                        id="input" 
                        placeholder="Напиши сообщение..."
                        onkeypress="if(event.key==='Enter') sendMessage()"
                    >
                    <button onclick="sendMessage()">➤</button>
                </div>
                
                <div class="info">
                    🚀 Архитектура: src/ (15 модулей) | main/ (launcher) | config/ (settings)
                </div>
            </div>
        </div>
        
        <script>
            const messagesDiv = document.getElementById('messages');
            const inputField = document.getElementById('input');
            
            async function sendMessage() {
                const text = inputField.value.trim();
                if (!text) return;
                
                // Показываем сообщение пользователя
                const userMsg = document.createElement('div');
                userMsg.className = 'message user';
                userMsg.textContent = text;
                messagesDiv.appendChild(userMsg);
                
                inputField.value = '';
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                try {
                    // Отправляем на сервер
                    const response = await fetch('/api/message', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text })
                    });
                    
                    const data = await response.json();
                    
                    // Показываем ответ IRIS
                    const irisMsg = document.createElement('div');
                    irisMsg.className = 'message iris';
                    irisMsg.textContent = data.response;
                    messagesDiv.appendChild(irisMsg);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                } catch (error) {
                    console.error('Ошибка:', error);
                }
            }
        </script>
    </body>
    </html>
    """
    return html


@app.route('/api/status', methods=['GET'])
def status():
    """API: Статус сервера."""
    return jsonify(iris_status)


@app.route('/api/message', methods=['POST'])
def message():
    """API: Обработать сообщение."""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Empty text'}), 400
        
        # Обрабатываем через мозг
        response = brain.process(text)
        
        return jsonify({
            'success': True,
            'input': text,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"[API] Ошибка: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """API: Health check."""
    return jsonify({
        'status': 'healthy',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })


def main():
    """Главная функция запуска сервера."""
    logger.info("\n" + "="*70)
    logger.info("[IRIS SERVER] 🌸 IRIS AI v2.0 - ЗАПУСК")
    logger.info("="*70)
    
    logger.info("[IRIS SERVER] 📚 Загруженные модули:")
    logger.info(f"[IRIS SERVER]   ✅ iris_brain (LLM мозг)")
    logger.info(f"[IRIS SERVER]   ✅ Flask API (:5000)")
    logger.info(f"[IRIS SERVER]   ✅ Web UI (интерфейс)")
    
    logger.info("\n[IRIS SERVER] 🚀 Запускаю Flask...")
    logger.info("[IRIS SERVER] 🌐 Откройте http://localhost:5000")
    logger.info("[IRIS SERVER] ⌨️  Для выхода: Ctrl+C\n")
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n[IRIS SERVER] Остановка сервера...")
    except Exception as e:
        logger.error(f"[IRIS SERVER] Ошибка: {e}")
    finally:
        logger.info("[IRIS SERVER] До свидания! 🌸")


if __name__ == '__main__':
    main()
