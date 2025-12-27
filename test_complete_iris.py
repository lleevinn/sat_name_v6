#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_complete_iris.py - Полные тесты IRIS AI

Выполнение: python test_complete_iris.py
Ожидаемые результаты: Все модули работают
"""

import sys
import logging
import asyncio
from pathlib import Path

# Добавляем файл в PATH
sys.path.insert(0, str(Path(__file__).parent))

from iris_ai.iris_brain_complete import IrisAI, test_iris_initialization, test_iris_reactions, test_iris_llm

# ======== LOGGING ========
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def print_header(text: str):
    """Печать заголовка."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def run_complete_tests():
    """Полные тесты IRIS."""
    
    print_header("🌸 IRIS AI v1.0 - ПОЛНЫЕ ТЕСТЫ")
    
    # ТЕСТ 1: Инициализация
    iris = test_iris_initialization()
    
    if not iris:
        logger.error("✗ Не удалось инициализировать IRIS")
        logger.error("✗ Проверь:")
        logger.error("   1. Ollama руннинг на localhost:11434?")
        logger.error("   2. Модель Qwen или другая установлена?")
        return
    
    # ТЕСТ 2: Реакции
    test_iris_reactions(iris)
    
    # ТЕСТ 3: LLM
    test_iris_llm(iris)
    
    # ФИНАЛЬНЫМ Отчёт
    print_header("✅ ВСЕ ТЕСТЫ ПРОйДЕНЫ!")
    logger.info("🌸 IRIS готова к брой")
    logger.info("💫 Читай docs/START_HERE.md для следующих шагов")
    logger.info("🚀 Давай создавать магию!\n")

if __name__ == "__main__":
    run_complete_tests()
