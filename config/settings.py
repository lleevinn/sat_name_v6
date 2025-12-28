#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config/settings.py - Центральная конфигурация IRIS AI

Описание:
    Все настройки IRIS в одном файле.
    Вся интеграция, модели, параметры LLM, голос, итд.

Модели LLM:
    - qwen3:4b-instruct (РЕКОМЕНДУЕТСЯ) ← отличные реплики, русский
    - qwen2.5-coder:1.5b ← быстра, менее адекватна
    - llama3.1:8b ← мощна, но медленна
    - deepseek-coder:6.7b ← для анализа кода

Температура (креативность):
    - 0.7 ← твёрдые, ответственные ответы
    - 0.8 ← хорошо (текущее значение)
    - 0.9 ← живые, творческие
    - 1.2 ← дикие, случайные
"""

from dataclasses import dataclass
from typing import Dict, Optional

# ============================================================================
# ГЛАВНЫЕ НАСТРОЙКИ (меняй эти!)
# ============================================================================

# Модель LLM для IRIS
PRIMARY_MODEL = "qwen3:4b-instruct"

# Температура (креативность ответов)
TEMPERATURE = 0.8

# Максимум токенов в ответе
MAX_TOKENS = 150

# Ollama сервер (локальный LLM)
OLLAMA_HOST = "http://localhost:11434"

# TTS голос (Edge TTS)
TTS_VOICE = "ru-RU-SvetlanaNeural"

# Debug режим
DEBUG = False


# ============================================================================
# ПРЕДУСТАНОВКИ (готовые наборы параметров)
# ============================================================================

@dataclass
class ConfigPreset:
    """Предустановка конфигурации."""
    name: str
    description: str
    model: str
    temperature: float
    max_tokens: int
    ollama_host: str
    tts_voice: str


class IrisConfig:
    """Центральная конфигурация IRIS AI с предустановками."""

    # QUICK - для повседневного использования (рекомендуется)
    QUICK = ConfigPreset(
        name="quick",
        description="Оптимальные параметры для повседневного использования",
        model="qwen3:4b-instruct",
        temperature=0.8,
        max_tokens=150,
        ollama_host="http://localhost:11434",
        tts_voice="ru-RU-SvetlanaNeural"
    )

    # FAST - быстрая, но менее умная
    FAST = ConfigPreset(
        name="fast",
        description="Очень быстрая, но могут быть менее умные ответы",
        model="qwen2.5-coder:1.5b",
        temperature=0.7,
        max_tokens=100,
        ollama_host="http://localhost:11434",
        tts_voice="ru-RU-SvetlanaNeural"
    )

    # POWERFUL - мощная, но медленнее
    POWERFUL = ConfigPreset(
        name="powerful",
        description="Мощная модель, но медленнее",
        model="llama3.1:8b",
        temperature=0.9,
        max_tokens=250,
        ollama_host="http://localhost:11434",
        tts_voice="ru-RU-SvetlanaNeural"
    )

    # CREATIVE - креативные и дикие ответы
    CREATIVE = ConfigPreset(
        name="creative",
        description="Креативные и случайные ответы",
        model="qwen3:4b-instruct",
        temperature=1.2,
        max_tokens=200,
        ollama_host="http://localhost:11434",
        tts_voice="ru-RU-SvetlanaNeural"
    )

    @classmethod
    def get_preset(cls, preset_name: str) -> ConfigPreset:
        """Получить предустановку по имени."""
        presets = {
            "quick": cls.QUICK,
            "fast": cls.FAST,
            "powerful": cls.POWERFUL,
            "creative": cls.CREATIVE
        }
        return presets.get(preset_name.lower(), cls.QUICK)

    @classmethod
    def get_all_presets(cls) -> Dict[str, ConfigPreset]:
        """Получить все доступные предустановки."""
        return {
            "quick": cls.QUICK,
            "fast": cls.FAST,
            "powerful": cls.POWERFUL,
            "creative": cls.CREATIVE
        }


# ============================================================================
# ИНТЕГРАЦИИ
# ============================================================================

class IntegrationsConfig:
    """Конфигурация интеграций с внешними сервисами."""

    # StreamElements интеграция
    STREAMELEMENTS = {
        "enabled": True,
        "api_url": "https://api.streamelements.com/v2",
        "description": "StreamElements API для аналитики"
    }

    # CS2 GSI (Game State Integration)
    CS2_GSI = {
        "enabled": True,
        "listen_host": "localhost",
        "listen_port": 3000,
        "description": "Counter-Strike 2 Game State Integration"
    }

    # Flask API сервер
    FLASK_API = {
        "enabled": True,
        "host": "localhost",
        "port": 5000,
        "debug": False,
        "description": "REST API сервер для управления IRIS"
    }


# ============================================================================
# ПУТИ И ФАЙЛЫ
# ============================================================================

class PathsConfig:
    """Конфигурация путей в проекте."""

    # Основные папки
    PROJECT_ROOT = "."
    SRC_DIR = "src"
    CONFIG_DIR = "config"
    UTILS_DIR = "utils"
    EXAMPLES_DIR = "examples"
    DOCS_DIR = "docs"
    MAIN_DIR = "main"

    # Логи и данные
    LOGS_DIR = "logs"
    DATA_DIR = "data"
    CACHE_DIR = ".cache"


# ============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================

"""
Примеры использования конфигурации:

# Использовать предустановку QUICK
from config.settings import IrisConfig
config = IrisConfig.get_preset("quick")
model = config.model
temp = config.temperature

# Использовать все доступные предустановки
all_presets = IrisConfig.get_all_presets()
for name, preset in all_presets.items():
    print(f"{name}: {preset.description}")

# Использовать интеграции
from config.settings import IntegrationsConfig
if IntegrationsConfig.CS2_GSI["enabled"]:
    port = IntegrationsConfig.CS2_GSI["listen_port"]
"""
