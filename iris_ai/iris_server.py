#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_server.py - ДОЛГОЖИВУЩИЙ FLASK СЕРВЕР ДЛЯ IRIS

Это основной сервер, который запускается ОДИН РАЗ и остаётся включённым
во время всего стрима. Слушает события от CS2 и другие пинги.

Использование:
    python iris_ai/iris_server.py
    # Сервер запустится на http://localhost:5000

Данные отправляются POST запросами:
    curl -X POST http://localhost:5000/event \
      -H "Content-Type: application/json" \
      -d '{"type": "kill", "kills": 3, "weapon": "AWP"}'
"""

import logging
import sys
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify
from datetime import datetime

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Импортируем IRIS
sys.path.insert(0, str(Path(__file__).parent))
from iris_brain_complete import IrisAI
from iris_config import IrisConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('iris_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Создаём Flask приложение
app = Flask(__name__)

# ГЛОБАЛЬНАЯ переменная для IRIS (инициализируется один раз при старте)
iris_instance = None

def init_iris():
    """Инициализировать IRIS один раз."""
    global iris_instance
    
    try:
        logger.info("[IRIS] Инициализирую IRIS...")
        
        config = IrisConfig.get_preset("quick")
        iris_instance = IrisAI(
            model=config["model"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            debug=False  # Меньше логов в продакшене
        )
        
        # Тест соединения
        if iris_instance.test_connection():
            logger.info("[IRIS] ✅ Успешно инициализирована!")
            logger.info(f"[IRIS] Модель: {config['model']}")
            logger.info(f"[IRIS] Температура: {config['temperature']}")
            return True
        else:
            logger.error("[IRIS] ❌ Не удалось подключиться к Ollama")
            return False
    
    except Exception as e:
        logger.error(f"[IRIS] ❌ Ошибка инициализации: {e}")
        logger.error("[IRIS] Проверь:")
        logger.error("   1. Ollama запущена? (ollama serve)")
        logger.error("   2. Модель загружена? (ollama run qwen3:4b-instruct)")
        return False

@app.before_request
def check_iris():
    """Проверить что IRIS готов."""
    if iris_instance is None:
        return jsonify({"error": "IRIS не инициализирована"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Проверить здоровье сервера."""
    return jsonify({
        "status": "healthy" if iris_instance else "initializing",
        "timestamp": datetime.now().isoformat(),
        "iris": "ready" if iris_instance else "initializing"
    })

@app.route('/event', methods=['POST'])
def handle_event():
    """
    Обработать игровое событие от CS2.
    
    Ожидаемые события:
    - kill: {"type": "kill", "kills": 3, "weapon": "AWP"}
    - death: {"type": "death", "killer": "Enemy"}
    - achievement: {"type": "achievement", "name": "Пентакилл"}
    - low_health: {"type": "low_health", "health": 15}
    - custom: {"type": "custom", "message": "Любой текст"}
    """
    try:
        data = request.get_json()
        
        if not data or 'type' not in data:
            return jsonify({"error": "Требуется поле 'type'"}), 400
        
        event_type = data.get('type')
        
        # Логируем событие
        logger.info(f"[EVENT] {event_type.upper()}: {data}")
        
        # Анализируем событие
        if event_type == 'custom':
            # Кастомное сообщение
            message = data.get('message', 'неизвестное сообщение')
            response = iris_instance.generate_response(
                f"Ты IRIS. Ответь кратко (1-2 предложения) на русском на: {message}"
            )
        else:
            # Стандартное игровое событие
            response = iris_instance.analyze_game_event(event_type, data)
        
        logger.info(f"[RESPONSE] {response}")
        
        return jsonify({
            "status": "ok",
            "event": event_type,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Ошибка обработки события: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/say', methods=['POST'])
def say():
    """
    Генерировать ответ на произвольный текст.
    
    Использование:
        curl -X POST http://localhost:5000/say \
          -H "Content-Type: application/json" \
          -d '{"text": "Как дела?"}'
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Требуется поле 'text'"}), 400
        
        logger.info(f"[SAY] {text}")
        
        response = iris_instance.generate_response(
            f"Ты IRIS. Ответь кратко (1-2 предложения) на русском.\n\n"
            f"Вопрос: {text}\nОтвет IRIS:"
        )
        
        logger.info(f"[RESPONSE] {response}")
        
        return jsonify({
            "status": "ok",
            "input": text,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Ошибка в /say: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/info', methods=['GET'])
def info():
    """Получить информацию о IRIS."""
    if not iris_instance:
        return jsonify({"error": "IRIS не инициализирована"}), 500
    
    return jsonify({
        "name": "IRIS",
        "version": "1.0",
        "model": iris_instance.model,
        "temperature": iris_instance.temperature,
        "max_tokens": iris_instance.max_tokens,
        "status": "running",
        "uptime": datetime.now().isoformat()
    })

@app.route('/context', methods=['GET', 'POST'])
def context():
    """
    Управлять контекстом разговора.
    
    GET: Получить текущий контекст
    POST: Добавить сообщение в контекст
        {"role": "user", "content": "Привет IRIS!"}
    """
    if request.method == 'GET':
        return jsonify({
            "context_length": len(iris_instance.context),
            "context": iris_instance.context[-5:]  # Последние 5 сообщений
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        role = data.get('role', 'user')
        content = data.get('content', '')
        
        iris_instance.add_context(content, role)
        
        return jsonify({
            "status": "ok",
            "message": f"Добавлено в контекст: {role} - {content[:50]}..."
        })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint не найден"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Внутренняя ошибка сервера"}), 500

def main():
    """
    Запустить IRIS сервер.
    
    Инструкции:
    1. iris_server.py запускается один раз
    2. Остаётся включённым во время всего стрима
    3. Принимает события от CS2 через HTTP POST
    4. Генерирует голосовые ответы в реальном времени
    """
    
    logger.info("\n" + "="*60)
    logger.info("[IRIS] ЗАПУСК ДОЛГОЖИВУЩЕГО СЕРВЕРА")
    logger.info("="*60)
    
    # Инициализируем IRIS
    if not init_iris():
        logger.error("[FATAL] IRIS не инициализирована. Выходим.")
        sys.exit(1)
    
    # Запускаем Flask
    logger.info("\n[SERVER] Запускаю Flask сервер...")
    logger.info("[SERVER] 🚀 Сервер доступен на http://localhost:5000")
    logger.info("[SERVER] 📊 Endpoints:")
    logger.info("[SERVER]   GET  /health         - Проверить здоровье")
    logger.info("[SERVER]   POST /event          - Отправить событие")
    logger.info("[SERVER]   POST /say            - Генерировать ответ")
    logger.info("[SERVER]   GET  /info           - Информация о IRIS")
    logger.info("[SERVER]   GET  /context        - Получить контекст")
    logger.info("[SERVER] \n[SERVER] IRIS готова! Ожидаю события...\n")
    
    try:
        # Запускаем на всех интерфейсах (доступна с других компьютеров)
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # НИКОГДА не используй debug=True в продакшене!
            use_reloader=False  # Не перезагружаемся при изменениях файлов
        )
    except KeyboardInterrupt:
        logger.info("\n[SERVER] Завершение работы...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[FATAL] Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
