#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_launcher_debug.py - Лаунчер с выводом логов в реальном времени
Использует для тестирования и отладки!

Запуск:
    python iris_launcher_debug.py

Что запускает:
    1. iris_ai/iris_server.py (порт 5000) - основной сервер IRIS
    2. test_cs2_gsi.py (подключается к 5000) - слушатель событий CS2
"""

import logging
import sys
import os
import subprocess
import time
import threading
from pathlib import Path

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

class DebugLauncher:
    """Лаунчер с выводом логов в реальном времени."""
    
    def __init__(self):
        self.processes = {}
        self.iris_path = Path(__file__).parent / 'iris_ai'
        self.project_root = Path(__file__).parent
    
    def run_module(self, name, script, delay=0):
        """Запустить модуль с выводом логов."""
        if delay > 0:
            logger.info(f"⏳ Жду {delay} сек перед запуском {name}...")
            time.sleep(delay)
        
        logger.info(f"\n🚀 Запускаю {name}...")
        
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
                        # Выводим логи из подпроцесса с приставкой
                        print(f"[{name}] {line.rstrip()}")
            except:
                pass
            finally:
                logger.warning(f"[{name}] Процесс завершился")
        
        thread = threading.Thread(target=read_logs, daemon=True)
        thread.start()
        
        return process
    
    def run(self):
        """Главный цикл."""
        logger.info("\n" + "="*70)
        logger.info("🌸 IRIS DEBUG LAUNCHER - ПОЛНАЯ ИНТЕГРАЦИЯ 🌸")
        logger.info("="*70)
        logger.info("📋 Запускаемые модули:")
        logger.info("   1️⃣  iris_ai/iris_server.py (порт 5000) - IRIS Brain")
        logger.info("   2️⃣  test_cs2_gsi.py (событий CS2 → 5000)")
        logger.info("="*70)
        
        try:
            # Запускаем обязательные модули
            logger.info("\n[ФАЗА 1] Инициализация основного сервера...")
            
            # IRIS Server - основной долгоживущий сервер
            self.run_module(
                "🧠 IRIS Server",
                self.iris_path / 'iris_server.py',
                delay=0
            )
            
            # Даём серверу время на инициализацию Ollama
            logger.info("\n⏳ Даю серверу время на инициализацию (3 сек)...")
            time.sleep(3)
            
            logger.info("\n[ФАЗА 2] Запуск слушателя событий CS2...")
            
            # CS2 GSI - слушатель событий
            self.run_module(
                "🎮 CS2 GSI",
                self.project_root / 'test_cs2_gsi.py',
                delay=1
            )
            
            logger.info("\n" + "="*70)
            logger.info("✅ ВСЕ МОДУЛИ ЗАПУЩЕНЫ!")
            logger.info("="*70)
            logger.info("📊 СТАТУС:")
            logger.info("   ✅ IRIS Server слушает на http://localhost:5000")
            logger.info("   ✅ CS2 GSI готов к событиям")
            logger.info("="*70)
            logger.info("🎮 ТЕСТИРОВАНИЕ:")
            logger.info("   1. Зайди в CS2 как ИГРОК (не зритель!)")
            logger.info("   2. Убей кого-то")
            logger.info("   3. Смотри логи ниже 👇")
            logger.info("="*70)
            logger.info("🔴 Нажми Ctrl+C для выхода\n")
            
            # Ждём пока процессы работают
            while True:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Выключение...")
            for name, process in self.processes.items():
                try:
                    logger.info(f"  Останавливаю {name}...")
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            logger.info("✅ Готово!")
            sys.exit(0)
        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            sys.exit(1)

def main():
    launcher = DebugLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
