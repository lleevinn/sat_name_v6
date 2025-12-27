#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_config.py - Настройки IRIS

Описание:
  Этот файл правильно конфигурирует IRIS
  для твоего энвайронмента.

Модели:
  - qwen3:4b-instruct (РЕКОМЕНДУЕТСЯ) ← ХОРОШИе реплики
  - qwen2.5-coder:1.5b ← Быстра в коде
  - llama3.1:8b ← Мощна, но медленна
  - deepseek-coder:6.7b ← Для анализа

Оптимизация:
  - temperature: 0.7 (дружелюбно-ответственно)
  - temperature: 0.9 (дыкю по архиву)
  - temperature: 1.2 (дюрные рандом ответы)
"""

# ======== ПОЛЮЗОВАТЕЛЬАЕМЫЕ НАСТОЙКИ ========

# Основна модель IRIS
# МЕНЯЙ: если ты хочешь другую
# Идеальные варианты:
#   - "qwen3:4b-instruct" ← ЛУЧШАЙ ВЫБОР (отличные реплики, русский)
#   - "qwen2.5-coder:1.5b" ← Быстра, менее адекватна
#   - "llama3.1:8b" ← Мощна, но медленна
PRIMAR_MODEL = "qwen3:4b-instruct"

# Температура (креативность)
# 0.7 = твердые, ответственные ответы
# 0.8 = хорошо (текущие а)
# 0.9 = живые, творческие
# 1.2 = дюные, случайные
TEMPERATURE = 0.8

# Максимум марков
# 150 = короткие реплики (IRIS принципиально короткая)
# 300 = средние
# 500+ = долгие
MAX_TOKENS = 150

# Ollama сервер
OLLAMA_HOST = "http://localhost:11434"

# VOSK модель (русская)
VOSK_MODEL_PATH = "model_ru"

# TTS голос (Edge TTS)
# Опционы:
#   - "ru-RU-SvetlanaNeural" (НОРМАЛьные женские)
#   - "ru-RU-DariyaNeural" (живая)
#   - "ru-RU-AlistairNeural" (мужской)
TTS_VOICE = "ru-RU-SvetlanaNeural"

# Дебаг мод (DEBUG)
DEBUG = False  # Поставь True если нужные детали

# ======== ПОНРАВИТОЧНО: Автоматические настройки ========

class IrisConfig:
    """Преднастроенные конфигурации для IRIS."""
    
    # QUICK START (рекомендуется для всех)
    QUICK = {
        "model": "qwen3:4b-instruct",
        "temperature": 0.8,
        "max_tokens": 150,
        "ollama_host": "http://localhost:11434",
        "description": "Оптимальные параметры для повседневного употребления"
    }
    
    # FAST (подразумевается жертва качество)
    FAST = {
        "model": "qwen2.5-coder:1.5b",
        "temperature": 0.7,
        "max_tokens": 100,
        "ollama_host": "http://localhost:11434",
        "description": "Очень быстрая, но могут быть менее умные ответы"
    }
    
    # POWERFUL (подразумевается настройка)
    POWERFUL = {
        "model": "llama3.1:8b",
        "temperature": 0.9,
        "max_tokens": 250,
        "ollama_host": "http://localhost:11434",
        "description": "Мощная, но медленная"
    }
    
    # CREATIVE (все дичо для радости)
    CREATIVE = {
        "model": "qwen3:4b-instruct",
        "temperature": 1.2,
        "max_tokens": 200,
        "ollama_host": "http://localhost:11434",
        "description": "Креативные и случайные ответы (оригинальные)"
    }
    
    @classmethod
    def get_preset(cls, preset_name: str) -> dict:
        """Получить преднастроенное."""
        presets = {
            "quick": cls.QUICK,
            "fast": cls.FAST,
            "powerful": cls.POWERFUL,
            "creative": cls.CREATIVE
        }
        return presets.get(preset_name.lower(), cls.QUICK)

# Пример использования:
# from iris_config import IrisConfig
# config = IrisConfig.get_preset("quick")
# iris = IrisAI(
#     model=config["model"],
#     temperature=config["temperature"],
#     max_tokens=config["max_tokens"]
# )
