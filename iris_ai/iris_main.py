#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_main.py - главный скрипт IRIS
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

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
        logging.FileHandler('iris.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class IrisManager:
    """Менеджер IRIS для управления и тестирования."""
    
    def __init__(self):
        self.iris = None
        self.config = IrisConfig.get_preset("quick")
    
    async def start(self) -> bool:
        """Инициализировать IRIS."""
        try:
            logger.info("[IRIS] Начинаю старт...")
            
            # Создаём IRIS БЕЗ vosk_model_path (не нужен)
            self.iris = IrisAI(
                model=self.config["model"],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"],
                debug=True
            )
            
            logger.info("[IRIS] Успешно инициализирована!")
            logger.info(f"[IRIS] Модель: {self.config['model']}")
            logger.info(f"[IRIS] Температура: {self.config['temperature']}")
            return True
        
        except Exception as e:
            logger.error(f"[IRIS] Ошибка старта: {e}")
            logger.error("[IRIS] Проверь:")
            logger.error("   1. Ollama запущена? (ollama serve)")
            logger.error(f"   2. Модель {self.config['model']} загружена? (ollama run {self.config['model']})")
            return False
    
    async def test_llm(self):
        """Тестировать LLM."""
        try:
            logger.info("[TEST] Генерирую ответ от IRIS...")
            
            prompt = """Ты IRIS - ассистент геймера CS2. Ответь кратко (1-2 предложения) на русском.
Промпт: Игрок только что убил 3 врага подряд!
Ответ IRIS:"""
            
            response = self.iris.generate_response(prompt)
            logger.info(f"[TEST] Ответ IRIS: {response}")
            return True
        
        except Exception as e:
            logger.error(f"[TEST] Ошибка LLM: {e}")
            return False
    
    async def run_full_test(self):
        """Запустить полный тест."""
        logger.info("\n" + "="*50)
        logger.info("[IRIS] ЗАПУСК ПОЛНОГО ТЕСТА")
        logger.info("="*50)
        
        # 1. Старт
        if not await self.start():
            logger.error("[IRIS] Ошибка инициализации")
            return
        
        # 2. Тест LLM
        logger.info("\n" + "-"*50)
        if await self.test_llm():
            logger.info("[SUCCESS] IRIS полностью работает!")
        else:
            logger.error("[ERROR] Ошибка при тестировании LLM")
        
        logger.info("-"*50)

async def main():
    """Главная функция."""
    manager = IrisManager()
    await manager.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())
