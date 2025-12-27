#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_complete_solution.py - ВСЁ В ОДНОМ ОКНЕ!

это решение лаунчит высёт в ОДНОМ ОКНе:
  1. IRIS мозг (Ollama LLM)
  2. Flask сервер
  3. CS2 GSI listener (слушает гру от CS2)
  4. Автоматически отправляет эвенты от игры в IRIS

Использование:
    python iris_ai/iris_complete_solution.py

Ничего менять не нужно - всё одно окно!
"""

import logging
import sys
import os
import threading
import time
from pathlib import Path

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Импортируем наши модули
sys.path.insert(0, str(Path(__file__).parent))

from iris_brain_complete import IrisAI
from iris_config import IrisConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('iris_complete.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class IRISCompleteSolution:
    """
    Волшебные решение: всё в ОДНОМ процессе!
    """
    
    def __init__(self):
        self.iris = None
        self.config = IrisConfig.get_preset("quick")
        self.running = True
        self.event_queue = []
        
        logger.info("\n" + "="*70)
        logger.info("[IRIS] Инициализация ПОЛНОГО рЕШЕНИЯ")
        logger.info("="*70)
    
    def init_iris_brain(self) -> bool:
        """Настроить МОЗГ IRIS."""
        try:
            logger.info("\n[IRIS] Инициализирую мозг...")
            
            self.iris = IrisAI(
                model=self.config["model"],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"],
                debug=False
            )
            
            if self.iris.test_connection():
                logger.info(f"[IRIS] ✅ Мозг включена!")
                logger.info(f"[IRIS] Модель: {self.config['model']}")
                logger.info(f"[IRIS] Температура: {self.config['temperature']}")
                return True
            else:
                logger.error("[IRIS] ❌ Не удалось подключиться к Ollama")
                return False
        
        except Exception as e:
            logger.error(f"[IRIS] ❌ Ошибка инициализации: {e}")
            return False
    
    def init_flask_server(self):
        """Настроить Flask сервер в отдельном потоке."""
        try:
            from flask import Flask, request, jsonify
            from datetime import datetime
            
            app = Flask(__name__)
            iris_ref = self.iris  # референсия на iris
            
            logger.info("\n[SERVER] Настраиваю Flask сервер...")
            
            @app.route('/health', methods=['GET'])
            def health():
                return jsonify({
                    "status": "healthy",
                    "iris": "ready",
                    "timestamp": datetime.now().isoformat()
                })
            
            @app.route('/event', methods=['POST'])
            def handle_event():
                try:
                    data = request.get_json()
                    if not data or 'type' not in data:
                        return jsonify({"error": "Требуется поле 'type'"}), 400
                    
                    event_type = data.get('type')
                    logger.info(f"[EVENT] {event_type.upper()}: {data}")
                    
                    response = iris_ref.analyze_game_event(event_type, data)
                    logger.info(f"[RESPONSE] {response}")
                    
                    return jsonify({
                        "status": "ok",
                        "event": event_type,
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    })
                
                except Exception as e:
                    logger.error(f"[ERROR] {e}")
                    return jsonify({"error": str(e)}), 500
            
            @app.route('/say', methods=['POST'])
            def say():
                try:
                    data = request.get_json()
                    text = data.get('text', '')
                    
                    if not text:
                        return jsonify({"error": "Требуется поле 'text'"}), 400
                    
                    logger.info(f"[SAY] {text}")
                    response = iris_ref.generate_response(
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
                    logger.error(f"[ERROR] {e}")
                    return jsonify({"error": str(e)}), 500
            
            logger.info("[SERVER] ✅ Flask настроен")
            
            # Запускаем в отдельном потоке
            server_thread = threading.Thread(
                target=lambda: app.run(
                    host='0.0.0.0',
                    port=5000,
                    debug=False,
                    use_reloader=False
                ),
                daemon=True
            )
            server_thread.start()
            logger.info("[SERVER] 🚀 Сервер запущен на http://localhost:5000")
        
        except Exception as e:
            logger.error(f"[SERVER] ❌ Ошибка: {e}")
    
    def init_gsi_listener(self):
        """Настроить GSI listener в отдельном потоке."""
        try:
            from flask import Flask, request, jsonify
            import threading
            
            logger.info("\n[GSI] Настраиваю CS2 GSI listener...")
            
            gsi_app = Flask(__name__)
            iris_ref = self.iris
            
            # сохраняем предыдущее состояние
            prev_health = 100
            prev_kills = 0
            prev_deaths = 0
            
            @gsi_app.route('/', methods=['POST'])
            def gsi_handler():
                nonlocal prev_health, prev_kills, prev_deaths
                
                try:
                    data = request.get_json()
                    if not data:
                        return jsonify({"status": "ok"})
                    
                    # Парсим данные
                    player = data.get('player', {})
                    state = player.get('state', {})
                    match_stats = player.get('match_stats', {})
                    
                    current_health = state.get('health', 100)
                    current_kills = match_stats.get('kills', 0)
                    current_deaths = match_stats.get('deaths', 0)
                    
                    # Отправляем эвенты
                    
                    # Убийство
                    if current_kills > prev_kills:
                        kills_delta = current_kills - prev_kills
                        
                        # Получаем раунд убийств
                        round_kills = state.get('round_kills', 0)
                        weapon = '?'
                        
                        # Пытаем вытащить наименование оружия
                        weapons = player.get('weapons', {})
                        for w_key, w_data in weapons.items():
                            if w_data.get('state') == 'active':
                                weapon = w_data.get('name', '?')
                                break
                        
                        logger.info(f"[GSI] Убийство! Раунд: {round_kills}, Оружие: {weapon}")
                        
                        # Отправляем в IRIS
                        response = iris_ref.analyze_game_event('kill', {
                            'type': 'kill',
                            'kills': round_kills,
                            'weapon': weapon
                        })
                        logger.info(f"[GSI] IRIS: {response}")
                    
                    # Мерть
                    if current_deaths > prev_deaths:
                        logger.info(f"[GSI] Смерть!")
                        response = iris_ref.analyze_game_event('death', {
                            'type': 'death',
                            'killer': 'Enemy'
                        })
                        logger.info(f"[GSI] IRIS: {response}")
                    
                    # Низкое здоровье
                    if current_health < prev_health and current_health > 0 and current_health <= 30:
                        logger.info(f"[GSI] Низкое здоровье: {current_health} HP")
                        response = iris_ref.analyze_game_event('low_health', {
                            'type': 'low_health',
                            'health': current_health
                        })
                        logger.info(f"[GSI] IRIS: {response}")
                    
                    # Обновляем стате
                    prev_health = current_health
                    prev_kills = current_kills
                    prev_deaths = current_deaths
                    
                    return jsonify({"status": "ok"})
                
                except Exception as e:
                    logger.error(f"[GSI] Ошибка: {e}")
                    return jsonify({"status": "ok"})
            
            logger.info("[GSI] ✅ GSI настроен")
            
            # Запускаем в отдельном потоке
            gsi_thread = threading.Thread(
                target=lambda: gsi_app.run(
                    host='0.0.0.0',
                    port=3000,
                    debug=False,
                    use_reloader=False
                ),
                daemon=True
            )
            gsi_thread.start()
            logger.info("[GSI] 🚀 GSI listener запущен на http://localhost:3000")
        
        except Exception as e:
            logger.error(f"[GSI] ❌ Ошибка: {e}")
    
    def print_ascii_art(self):
        """Показываем красивые логи :)"""
        ascii_art = """
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        \n
              ✨ IRIS ПОЛНОЕ РЕШЕНИЕ ✨
              🙋 Всё в ОДНОМ ОКНЕ! 🚀
        
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        
        🚣 Компоненты:
        ✅ IRIS Мозг - мыслит и отвечает
        ✅ Flask Server - слушает события
        ✅ GSI Listener - катчит события от CS2
        ✅ Auto Events - автоматически отправляет
        
        🌟 Порты:
        3000 - CS2 GSI
        5000 - IRIS HTTP API
        
        🔓 Хёк: Ctrl+C для выхода
        """
        logger.info(ascii_art)
    
    def run(self):
        """Запустить всё в ОДНОМ процессе."""
        
        try:
            # 1. Инициализируем мозг
            if not self.init_iris_brain():
                logger.error("[FATAL] IRIS не инициализирована")
                return
            
            # 2. Настраиваем Flask
            self.init_flask_server()
            time.sleep(1)  # Подождем запуска
            
            # 3. Настраиваем GSI
            self.init_gsi_listener()
            time.sleep(1)
            
            # Показываем статус
            self.print_ascii_art()
            
            logger.info("\n[READY] 🙋 IRIS ГОТОВА!")
            logger.info("[READY] 🌈 Весь мир ваш стрим!")
            logger.info("\n[WAITING] Ожидаю евентов...\n")
            
            # Остаемся живым
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n[SHUTDOWN] Нажат Ctrl+C...")
            logger.info("[GOODBYE] До свидания! 🙋")
            self.running = False
        except Exception as e:
            logger.error(f"[FATAL] {e}")

def main():
    solution = IRISCompleteSolution()
    solution.run()

if __name__ == "__main__":
    main()
