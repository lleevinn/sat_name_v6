#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_launcher.py - ПОНТОН ОТКРЫВАЮЩИЙ ОДНА ПОКВАЩНА ОНА РАсставляет ВСЕ ВЕЛиколепные

Философия:
  1. МОДУЛЬНОСТЬ - каждый компонент независим
  2. КУЧНОМРП - launcher сохраняет порядок
  3. РАСШИРЯЕМО Е - легко добавлять новые сервисы

Использование:
  python iris_ai/iris_launcher.py

Архитектура:
  [iris_launcher.py]
    ├── [ирис_сервер]
    ├── [cs2_gsi]
    ├── [войс_запись]
    ├── [desktop_control] (будющие)
    └── [memory_manager] (будющие)
"""

import logging
import sys
import os
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Dict, Optional

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
    """
    Пункт запуска всех IRIS процессов.
    
    Архитектура:
    - Каждый модуль в отдельном процессе (работает дольше)
    - Launcher открывает всё сразу
    - Если процесс падает - перезагружается
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.modules: Dict[str, Dict] = {}
        self.running = True
        self.iris_path = Path(__file__).parent
        self.project_root = self.iris_path.parent
        
        # Регистрируем модули
        self._register_modules()
        
        logger.info("\n" + "="*70)
        logger.info("[LAUNCHER] ПОНТОН IRIS - КОННЕКТОР ВСЕХ МОДУЛЕЙ")
        logger.info("="*70)
    
    def _register_modules(self):
        """Регистрируем все доступные модули."""
        
        # Core: IRIS Server (API + Brain)
        self.modules['iris_server'] = {
            'name': '🧠 IRIS Server',
            'script': self.iris_path / 'iris_server.py',
            'required': True,
            'description': 'API сервер + мозг IRIS',
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
        
        # Voice: Recording (future)
        self.modules['voice_recorder'] = {
            'name': '🎤 Voice Recorder',
            'script': self.iris_path / 'voice_recorder.py',
            'required': False,
            'description': 'Запись окружающего звука',
            'port': None
        }
        
        # Future: Desktop Control
        self.modules['desktop_control'] = {
            'name': '🖥️ Desktop Control',
            'script': self.iris_path / 'desktop_control.py',
            'required': False,
            'description': 'Управление компьютером (будущее)',
            'port': None
        }
        
        # Future: Memory Manager
        self.modules['memory_manager'] = {
            'name': '🗄️ Memory Manager',
            'script': self.iris_path / 'memory_manager.py',
            'required': False,
            'description': 'Память и контекст (будущее)',
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
                cwd=str(self.iris_path)
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
        logger.info("[LAUNCHER] ОБАЗАТЕЛЬНЫЕ МОДУЛИ")
        logger.info("="*70)
        
        for module_name, module_info in self.modules.items():
            if module_info['required']:
                if self._launch_module(module_name):
                    success_count += 1
                else:
                    fail_count += 1
        
        # Если падали обязательные - не все посначали
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
        """Мониторить все процессы и перезагружать при требовании."""
        logger.info("\n[MONITOR] Мониторинг процессов...\n")
        
        while self.running:
            try:
                # Проверяем статус каждого процесса
                for module_name, process in list(self.processes.items()):
                    if process.poll() is not None:  # Процесс упал
                        module = self.modules.get(module_name)
                        logger.warning(f"\n[MONITOR] ❌ {module['name']} упал!")
                        
                        # На данном этапе - просто оповещаем
                        # В будущем - добавим автоперезагружку
                        logger.warning(f"[MONITOR] В будущем будет автоперезагружка")
                
                time.sleep(5)  # Проверяем каждые 5 секунд
            
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
        """Показать витальные сообщения."""
        welcome = """
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        
               ✨ IRIS НОВАЯ АРХИТЕКТУРА ✨
               🌟 МОДУЛЬНАЯ, РАСШИРЯЕМАЯ, НАДЁЖНАЯ 🌟
        
        🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸 🌸
        
        🚣 Компоненты:
        ✅ Core: IRIS Server (port 5000)
        ✅ Integration: CS2 GSI (port 3000)
        ⚡ Voice: Recording & Control
        🔛 Future: Desktop Control, Memory Manager
        
        🚀 Модульная архитектура дают высокую масштабируемость.
        ✨ Каждый модуль может работать независимо.
        
        🔓 Выыд: Ctrl+C
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
            
            logger.info("\n[LAUNCHER] 🙋 IRIS ПОЛНОСТЬЮ АКТИВНА!")
            logger.info("[LAUNCHER] 🌟 Все модули работают")
            logger.info("[LAUNCHER] 🚣 Ожидаю событий...\n")
            
            # Мониторим процессы
            self.monitor()
        
        except KeyboardInterrupt:
            logger.info("\n[LAUNCHER] Нажат Ctrl+C")
        except Exception as e:
            logger.error(f"[LAUNCHER] Непредвиденная ошибка: {e}")
        finally:
            self.shutdown()
            logger.info("[LAUNCHER] До свидания! 🙋")

def main():
    launcher = IRISLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
