#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_main.py - ГЛАВНАЯ ТОЧКА ВХОДА для полной системы IRIS

Этот файл запускает ВСЁ что нужно:
1. IRIS Server (фоновый сервис с Ollama)
2. TTS Engine (женский голос с эмоциями)
3. Event Processor (обработка игровых событий)

Просто запусти:
  python iris_main.py

И всё будет работать! 🔊✨
"""

import logging
import sys
import os
import subprocess
import time
import threading
from pathlib import Path
from typing import Dict, List

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class IRISMainController:
    """
    ГЛАВНЫЙ КОНТРОЛЛЕР IRIS - управляет всеми компонентами.
    
    Структура:
    ├─ IRIS Server (Ollama + Flask)
    ├─ IRIS TTS Engine (Женский голос с эмоциями)
    ├─ Event Processor (Обработка CS2 событий)
    └─ Game Event Listener (Слушатель событий игры)
    """
    
    def __init__(self):
        """Инициализация главного контроллера."""
        self.project_root = Path(__file__).parent
        self.iris_path = self.project_root / 'iris_ai'
        
        self.processes = {}
        self.threads = {}
        self.is_running = False
        
        logger.info("\n" + "="*80)
        logger.info("🌸 IRIS MAIN CONTROLLER - ИНИЦИАЛИЗАЦИЯ")
        logger.info("="*80)
        logger.info(f"📍 Project Root: {self.project_root}")
        logger.info(f"📍 IRIS Path: {self.iris_path}")
    
    def _run_module(self, name: str, script: Path, description: str = "") -> subprocess.Popen:
        """
        Запустить модуль в отдельном процессе.
        
        Args:
            name: Имя модуля (для логирования)
            script: Путь к скрипту
            description: Описание модуля
            
        Returns:
            Process handle
        """
        logger.info(f"\n🚀 Запускаю {name}...")
        if description:
            logger.info(f"   📝 {description}")
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=str(self.project_root)
            )
            
            self.processes[name] = process
            logger.info(f"✅ {name} запущен (PID: {process.pid})")
            
            # Читаем логи из подпроцесса в отдельном потоке
            def read_logs():
                try:
                    for line in process.stdout:
                        if line.strip():
                            print(f"[{name}] {line.rstrip()}")
                except:
                    pass
            
            thread = threading.Thread(
                target=read_logs,
                name=f"{name}_log_reader",
                daemon=True
            )
            thread.start()
            self.threads[f"{name}_logs"] = thread
            
            return process
        
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске {name}: {e}")
            return None
    
    def _check_dependencies(self) -> bool:
        """
        Проверить наличие необходимых зависимостей.
        
        Returns:
            True если всё ОК
        """
        logger.info("\n🔍 Проверка зависимостей...")
        
        dependencies = {
            'pyttsx3': 'TTS Engine (женский голос)',
            'requests': 'HTTP запросы к IRIS Server',
            'flask': 'Web сервер IRIS',
        }
        
        missing = []
        for module, description in dependencies.items():
            try:
                __import__(module)
                logger.info(f"  ✅ {module:15} - {description}")
            except ImportError:
                logger.warning(f"  ❌ {module:15} - {description} (НЕ УСТАНОВЛЕН)")
                missing.append(module)
        
        if missing:
            logger.error(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}")
            logger.error(f"   Установи: pip install {' '.join(missing)}")
            return False
        
        logger.info("\n✅ Все зависимости установлены!")
        return True
    
    def _check_iris_server(self, timeout: int = 10) -> bool:
        """
        Проверить доступность IRIS Server.
        
        Args:
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            True если сервер доступен
        """
        import requests
        
        logger.info(f"\n⏳ Проверка IRIS Server (максимум {timeout}с)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get('http://localhost:5000/health', timeout=2)
                if response.status_code == 200:
                    logger.info("✅ IRIS Server доступна!")
                    return True
            except:
                pass
            
            time.sleep(1)
        
        logger.warning("⚠️  IRIS Server не ответила за отведённое время")
        return False
    
    def start(self):
        """
        Запустить полную систему IRIS.
        
        Порядок запуска:
        1. Проверка зависимостей
        2. IRIS Server (Ollama + Flask)
        3. TTS Engine
        4. Event Listener
        """
        logger.info("\n" + "="*80)
        logger.info("🌟 ЗАПУСК ПОЛНОЙ СИСТЕМЫ IRIS")
        logger.info("="*80)
        
        # 1. Проверка зависимостей
        if not self._check_dependencies():
            logger.error("\n❌ Установи отсутствующие зависимости и попробуй снова!")
            return False
        
        # 2. Запускаем IRIS Server
        logger.info("\n[ЭТАП 1/3] Запуск IRIS Server...")
        iris_server = self._run_module(
            "🧠 IRIS Server",
            self.iris_path / 'iris_server.py',
            "Flask + Ollama для генерации ответов"
        )
        
        if not iris_server:
            logger.error("❌ Не смог запустить IRIS Server")
            return False
        
        # Ждём инициализации сервера
        time.sleep(3)
        
        # Проверяем доступность
        if not self._check_iris_server():
            logger.error("❌ IRIS Server не доступна")
            logger.error("   Проверь: установлен ли Ollama? запущен ли на localhost:11434?")
            self.stop()
            return False
        
        # 3. Запускаем TTS Engine (в отдельном потоке, а не процессе)
        logger.info("\n[ЭТАП 2/3] Инициализация TTS Engine...")
        try:
            from iris_ai.iris_tts_integration import IRISGameEventListener
            self.game_listener = IRISGameEventListener()
            logger.info("✅ TTS Engine инициализирован")
            
            # Тестируем звук
            logger.info("\n🔊 Тестирую женский голос IRIS...")
            self.game_listener.bridge.tts.init_sound()
            self.game_listener.wait_for_speech(timeout=5)
            logger.info("✅ Голос работает!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TTS: {e}")
            self.stop()
            return False
        
        # 4. Готовны к работе
        logger.info("\n" + "="*80)
        logger.info("✅ ВСЕ КОМПОНЕНТЫ ИНИЦИАЛИЗИРОВАНЫ И РАБОТАЮТ!")
        logger.info("="*80)
        logger.info("\n🎮 IRIS готова к работе с CS2!")
        logger.info("\n📊 Статус:")
        logger.info("  🧠 IRIS Server: http://localhost:5000")
        logger.info("  🔊 TTS Engine: АКТИВЕН (женский голос с эмоциями)")
        logger.info("  🎮 Game Listener: ГОТОВ К СОБЫТИЯМ")
        logger.info("\n💡 Доступные команды:")
        logger.info("  - game_listener.process_kill_event() - убийство")
        logger.info("  - game_listener.process_death_event() - смерть")
        logger.info("  - game_listener.process_low_health_event() - мало HP")
        logger.info("  - game_listener.process_low_ammo_event() - мало патронов")
        logger.info("  - game_listener.enable_silence() - молчание")
        logger.info("\n🔴 Нажми Ctrl+C для выхода\n")
        
        self.is_running = True
        return True
    
    def stop(self):
        """
        Остановить все компоненты IRIS.
        """
        logger.info("\n\n🛑 Выключение IRIS...")
        
        self.is_running = False
        
        # Останавливаем все процессы
        for name, process in self.processes.items():
            try:
                logger.info(f"  Останавливаю {name}...")
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"  ⚠️  Ошибка при остановке {name}: {e}")
        
        logger.info("✅ IRIS выключена")
    
    def run_interactive(self):
        """
        Запустить интерактивный режим для тестирования.
        """
        logger.info("\n" + "="*80)
        logger.info("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ ТЕСТИРОВАНИЯ")
        logger.info("="*80)
        logger.info("\nДоступные команды:")
        logger.info("  1. kill   - Симулировать убийство")
        logger.info("  2. death  - Симулировать смерть")
        logger.info("  3. health - Симулировать низкое HP")
        logger.info("  4. ammo   - Симулировать мало патронов")
        logger.info("  5. silent - Включить молчание")
        logger.info("  6. stats  - Показать статистику")
        logger.info("  7. exit   - Выход")
        logger.info("\n" + "="*80 + "\n")
        
        while self.is_running:
            try:
                cmd = input("\n📝 Команда: ").strip().lower()
                
                if cmd == 'kill':
                    logger.info("\n🎯 Симулирую убийство...")
                    self.game_listener.process_kill_event({
                        'weapon': 'AWP',
                        'headshot': True,
                        'round_kills': 1
                    })
                    self.game_listener.wait_for_speech()
                
                elif cmd == 'death':
                    logger.info("\n☠️  Симулирую смерть...")
                    self.game_listener.process_death_event({
                        'kd_ratio': 1.5
                    })
                    self.game_listener.wait_for_speech()
                
                elif cmd == 'health':
                    logger.info("\n❤️  Симулирую низкое здоровье...")
                    self.game_listener.process_low_health_event({
                        'current_health': 15,
                        'armor': 25
                    })
                    self.game_listener.wait_for_speech()
                
                elif cmd == 'ammo':
                    logger.info("\n🔫 Симулирую мало патронов...")
                    self.game_listener.process_low_ammo_event({
                        'weapon': 'AK-47',
                        'ammo_magazine': 3
                    })
                    self.game_listener.wait_for_speech()
                
                elif cmd == 'silent':
                    logger.info("\n🤐 Включаю молчание на 10 сек...")
                    self.game_listener.enable_silence(duration=10.0)
                    logger.info("   (IRIS всё равно ответит на критические события!)")
                
                elif cmd == 'stats':
                    logger.info("\n📊 Статистика IRIS:")
                    stats = self.game_listener.get_stats()
                    logger.info(f"  Всего сообщений: {stats['total_messages']}")
                    logger.info(f"  Молчание активно: {stats['is_silent']}")
                    logger.info(f"  Очередь пуста: {stats['queue_empty']}")
                    logger.info(f"  Распределение эмоций: {stats['emotion_distribution']}")
                
                elif cmd == 'exit':
                    logger.info("\n👋 До свидания!")
                    break
                
                else:
                    logger.warning(f"❌ Неизвестная команда: {cmd}")
            
            except KeyboardInterrupt:
                logger.info("\n\n👋 До свидания!")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")


def main():
    """
    Главная функция - точка входа в приложение.
    """
    controller = IRISMainController()
    
    try:
        # Запускаем полную систему
        if not controller.start():
            logger.error("\n❌ Ошибка при запуске системы")
            sys.exit(1)
        
        # Запускаем интерактивный режим
        controller.run_interactive()
    
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Получен сигнал прерывания")
    
    finally:
        # Останавливаем всё
        controller.stop()
        logger.info("\n✅ Приложение завершено")


if __name__ == "__main__":
    main()
