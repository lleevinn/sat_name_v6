#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main/launcher.py - Основной launcher IRIS AI

Философия:
    1. МОДУЛЬНОСТЬ - каждый компонент независим
    2. НОВАЯ СТРУКТУРА - одна главная папка
    3. ПО НОВОМУ - всё чисто и логично

Использование:
    python main/launcher.py

Архитектура:
    [main/launcher.py]  (главный launcher)
        ├─ src/iris_server.py       (Flask API + LLM мозг)
        ├─ src/cs2_gsi.py         (Game State Integration)
        ├─ utils/voice_recorder.py (запись голоса)
        └─ config/settings.py     (конфигурация)
"""

import logging
import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

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
        logging.FileHandler('iris_launcher.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class IRISLauncher:
    """Основной launcher всех модулей IRIS.
    
    Новая архитектура:
    - src/               ← Production код (15 модулей)
    - config/           ← Конфигурация
    - utils/            ← Утилиты
    - examples/         ← Примеры
    - main/             ← Этот launcher
    - docs/             ← Документация
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.modules: Dict[str, Dict] = {}
        self.running = True
        self.main_path = Path(__file__).parent
        self.project_root = self.main_path.parent
        
        # Регистрируем модули
        self._register_modules()
        
        logger.info("\n" + "="*70)
        logger.info("[LAUNCHER] ✨ IRIS AI - НОВАЯ АРХИТЕКТУРА")
        logger.info("="*70)
    
    def _register_modules(self):
        """Регистрируем все доступные модули."""
        
        # Core: IRIS Server (API + Brain)
        self.modules['iris_server'] = {
            'name': '🧠 IRIS Server',
            'script': self.project_root / 'src' / 'iris_server.py',
            'required': True,
            'description': 'Flask API сервер + LLM мозг',
            'port': 5000
        }
        
        # Integration: CS2 GSI
        self.modules['cs2_gsi'] = {
            'name': '🎮 CS2 GSI',
            'script': self.project_root / 'src' / 'cs2_gsi.py',
            'required': True,
            'description': 'Листенер событий Counter-Strike 2',
            'port': 3000
        }
        
        # Voice: Recording
        self.modules['voice_recorder'] = {
            'name': '🎙️ Voice Recorder',
            'script': self.project_root / 'utils' / 'voice_recorder.py',
            'required': False,
            'description': 'Запись окружающего звука',
            'port': None
        }
    
    def _launch_module(self, module_name: str) -> bool:
        """Запустить один модуль."""
        module = self.modules.get(module_name)
        if not module:
            logger.error(f"[LAUNCHER] Модуль '{module_name}' не зарегистрирован")
            return False
        
        # Проверяем что файл существует
        if not module['script'].exists():
            msg = f"[LAUNCHER] Ошибка: файл {module['script'].name} не найден"
            logger.error(msg)
            if module['required']:
                logger.error(f"[LAUNCHER] Этот модуль обязательный")
                return False
            else:
                logger.warning(f"[LAUNCHER] Пропускаю (дополнительный)")
                return True
        
        try:
            logger.info(f"\n[LAUNCHER] Запускаю {module['name']}...")
            logger.info(f"[LAUNCHER] {module['description']}")
            if module['port']:
                logger.info(f"[LAUNCHER] Port: {module['port']}")
            
            # Запускаем процесс
            process = subprocess.Popen(
                [sys.executable, str(module['script'])],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                cwd=str(self.project_root)
            )
            
            self.processes[module_name] = process
            logger.info(f"[LAUNCHER] ✅ {module['name']} запущен (PID: {process.pid})")
            return True
        
        except Exception as e:
            logger.error(f"[LAUNCHER] ❌ Ошибка запуска: {e}")
            if module['required']:
                return False
            return True
    
    def launch_all(self) -> bool:
        """Запустить все обязательные модули и доступные дополнительные."""
        
        success_count = 0
        fail_count = 0
        
        # Запускаем обязательные модули
        logger.info("\n" + "="*70)
        logger.info("[LAUNCHER] ОБЯЗАТЕЛЬНЫЕ МОДУЛИ")
        logger.info("="*70)
        
        for module_name, module_info in self.modules.items():
            if module_info['required']:
                if self._launch_module(module_name):
                    success_count += 1
                else:
                    fail_count += 1
        
        # Если падали обязательные - не все понесли
        if fail_count > 0:
            logger.error(f"[LAUNCHER] ❌ Не все обязательные модули запустились")
            return False
        
        # Запускаем дополнительные модули
        logger.info("\n" + "="*70)
        logger.info("[LAUNCHER] ДОПОЛНИТЕЛЬНЫЕ МОДУЛИ (Опциональные)")
        logger.info("="*70)
        
        for module_name, module_info in self.modules.items():
            if not module_info['required']:
                self._launch_module(module_name)
        
        return True
    
    def print_status(self):
        """Показать статус всех процессов."""
        logger.info("\n" + "="*70)
        logger.info("[STATUS] Процессы")
        logger.info("="*70)
        
        for module_name, process in self.processes.items():
            module = self.modules.get(module_name)
            if module:
                status = "✅ Нормально" if process.poll() is None else "❌ Остановлен"
                logger.info(f"  {module['name']:<30} {status} (PID: {process.pid})")
    
    def monitor(self):
        """Мониторить все процессы."""
        logger.info("\n[MONITOR] Мониторинг процессов...\n")
        
        while self.running:
            try:
                # Проверяем статус каждого процесса
                for module_name, process in list(self.processes.items()):
                    if process.poll() is not None:  # Процесс упал
                        module = self.modules.get(module_name)
                        logger.warning(f"\n[MONITOR] ❌ {module['name']} упал!")
                
                time.sleep(5)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"[MONITOR] Ошибка мониторинга: {e}")
    
    def shutdown(self):
        """Остановить все процессы."""
        logger.info("\n[SHUTDOWN] Останавливаю все процессы...")
        self.running = False
        
        for module_name, process in self.processes.items():
            try:
                module = self.modules.get(module_name)
                logger.info(f"[SHUTDOWN] Останавливаю {module['name']}...")
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.error(f"[SHUTDOWN] Ошибка: {e}")
        
        logger.info("[SHUTDOWN] Все процессы остановлены")
    
    def print_welcome(self):
        """Показать приветственные сообщения."""
        welcome = """
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        
               ✨ IRIS AI НОВАЯ АРХИТЕКТУРА ✨
               🌟 МОДУЛЬНАЯ, ЧИСТАЯ, НАДЁЖНАЯ 🌟
        
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        
        😠 Компоненты:
        ✅ Core: IRIS Server (port 5000)
        ✅ Integration: CS2 GSI (port 3000)
        ✅ Utilities: Этилиты и впомогательные
        ✅ Examples: Примеры использования
        
        🧠 Новая структура:
        ✅ src/          ← Production код (15 модулей)
        ✅ main/         ← Главные launcherы
        ✅ config/       ← Конфигурация
        ✅ utils/        ← Утилиты
        ✅ examples/     ← Примеры
        ✅ docs/         ← Документация
        
        🔼 Выход: Ctrl+C
        """
        logger.info(welcome)
    
    def run(self):
        """Главное цикл."""
        try:
            self.print_welcome()
            
            # Запускаем все модули
            if not self.launch_all():
                logger.error("[LAUNCHER] Ошибка запуска обязательных модулей")
                self.shutdown()
                return
            
            # Ожидаем немно для запуска
            time.sleep(2)
            
            # Показываем статус
            self.print_status()
            
            logger.info("\n[LAUNCHER] 😋 IRIS ПОЛНОСТЬЮ АКТИВНА!")
            logger.info("[LAUNCHER] 🌟 Все модули работают")
            logger.info("[LAUNCHER] 👋 Ожидаю событий...\n")
            
            # Мониторим процессы
            self.monitor()
        
        except KeyboardInterrupt:
            logger.info("\n[LAUNCHER] Нажат Ctrl+C")
        except Exception as e:
            logger.error(f"[LAUNCHER] Непредвиденная ошибка: {e}")
        finally:
            self.shutdown()
            logger.info("[LAUNCHER] До свидания! 😋")


def main():
    launcher = IRISLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
