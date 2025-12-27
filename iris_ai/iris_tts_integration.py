#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_tts_integration.py - Интеграция TTS Engine с обработчиком событий

Этот модуль соединяет:
- IRIS TTS Engine (женский голос с эмоциями)
- Async Event Processor (приоритетная очередь)
- CS2 Game Events (события из игры)

Результат: IRIS говорит в реальном времени на события игры!
"""

import logging
import sys
import os
import threading
import time
from typing import Dict, Optional, Callable
from queue import Queue, Empty
from pathlib import Path

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Импортируем IRIS TTS Engine
from iris_tts_emotion import IRISTTSEngine, EmotionType

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class IRISSpeechBridge:
    """
    Мост между обработчиком событий и TTS Engine.
    
    Функции:
    - Слушает события из игры
    - Передаёт их в IRIS TTS Engine
    - IRIS реагирует женским голосом с эмоциями
    """
    
    def __init__(self):
        """Инициализация моста между событиями и речью."""
        self.tts = IRISTTSEngine()
        self.event_handlers = {}
        self.is_running = False
        self.event_queue = Queue()
        
        logger.info("✅ IRIS Speech Bridge инициализирована")
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Зарегистрировать обработчик события.
        
        Args:
            event_type: Тип события (kill, death, low_health и т.д.)
            handler: Функция-обработчик
        """
        self.event_handlers[event_type] = handler
        logger.info(f"📌 Обработчик зарегистрирован: {event_type}")
    
    def on_kill_event(self, data: Dict):
        """Обработка события убийства."""
        self.tts.on_kill(data)
    
    def on_death_event(self, data: Dict):
        """Обработка события смерти."""
        self.tts.on_death(data)
    
    def on_low_health_event(self, data: Dict):
        """Обработка события низкого здоровья (КРИТИЧЕСКОЕ)."""
        self.tts.on_low_health(data)
    
    def on_low_ammo_event(self, data: Dict):
        """Обработка события мало патронов (КРИТИЧЕСКОЕ)."""
        self.tts.on_low_ammo(data)
    
    def on_game_start_event(self):
        """Обработка события начала раунда."""
        self.tts.on_game_start()
    
    def on_round_end_event(self, team_won: bool):
        """Обработка события конца раунда."""
        self.tts.on_round_end(team_won)
    
    def on_custom_event(self, text: str, emotion: str = "normal"):
        """Пользовательское сообщение с эмоцией."""
        self.tts.on_custom_message(text, emotion)
    
    def get_context(self) -> Dict:
        """Получить контекст разговора IRIS."""
        return self.tts.get_context()
    
    def get_conversation_history(self) -> list:
        """Получить историю разговора IRIS."""
        return self.tts.get_conversation_history()
    
    def wait_for_speech(self, timeout: float = None):
        """Ждать пока IRIS заканчивает говорить."""
        self.tts.wait_for_speech(timeout)


class IRISVoiceController:
    """
    Контроллер голоса IRIS - управление речью в реальном времени.
    
    Поддерживает:
    - Прерывание речи когда нужно
    - Молчание в критические моменты
    - Смена тона в зависимости от ситуации
    """
    
    def __init__(self, bridge: IRISSpeechBridge):
        """Инициализация контроллера голоса.
        
        Args:
            bridge: IRISSpeechBridge для взаимодействия с IRIS
        """
        self.bridge = bridge
        self.tts = bridge.tts
        self.is_silent = False
        self.silence_start = None
        
        logger.info("🎙️  IRIS Voice Controller инициализирована")
    
    def enable_silence(self, duration: float = 5.0):
        """
        Включить режим молчания (для критических моментов).
        
        Args:
            duration: Длительность молчания в секундах
        """
        self.is_silent = True
        self.silence_start = time.time()
        self.tts.clear_queue()
        logger.warning(f"🤐 IRIS переведена в режим молчания на {duration}с")
        
        # Отключить молчание после duration
        threading.Timer(
            duration,
            lambda: setattr(self, 'is_silent', False)
        ).start()
    
    def disable_silence(self):
        """Отключить режим молчания."""
        self.is_silent = False
        self.silence_start = None
        logger.info("🔊 IRIS молчание отключено")
    
    def should_speak(self, event_type: str) -> bool:
        """
        Определить, должна ли IRIS говорить сейчас.
        
        Args:
            event_type: Тип события
            
        Returns:
            True если IRIS должна говорить
        """
        # КРИТИЧЕСКИЕ события всегда говорят
        if event_type in ['low_health', 'low_ammo']:
            return True
        
        # Если в режиме молчания, не говорим
        if self.is_silent:
            return False
        
        return True
    
    def get_emotion_for_event(self, event_type: str, context: Dict = None) -> EmotionType:
        """
        Выбрать эмоцию для события на основе контекста.
        
        Args:
            event_type: Тип события
            context: Контекст игры
            
        Returns:
            EmotionType для события
        """
        if event_type == 'kill':
            return EmotionType.EXCITED
        elif event_type == 'death':
            return EmotionType.CALM
        elif event_type == 'low_health':
            return EmotionType.URGENT
        elif event_type == 'low_ammo':
            return EmotionType.URGENT
        elif event_type == 'game_start':
            return EmotionType.EXCITED
        elif event_type == 'round_end':
            return EmotionType.EXCITED
        else:
            return EmotionType.NORMAL
    
    def get_stats(self) -> Dict:
        """Получить статистику использования IRIS."""
        context = self.bridge.get_context()
        history = self.bridge.get_conversation_history()
        
        return {
            'total_messages': len(history),
            'is_silent': self.is_silent,
            'queue_empty': self.tts.is_queue_empty(),
            'emotion_distribution': self.tts.get_emotions_stats(),
            'last_message': history[-1] if history else None
        }


class IRISGameEventListener:
    """
    Слушатель событий игры - преобразует события в речь IRIS.
    
    Использование:
    listener = IRISGameEventListener()
    listener.process_kill_event({'weapon': 'AWP', 'headshot': True})
    listener.process_death_event({'kd_ratio': 1.5})
    """
    
    def __init__(self):
        """Инициализация слушателя событий."""
        self.bridge = IRISSpeechBridge()
        self.controller = IRISVoiceController(self.bridge)
        
        logger.info("🎮 IRIS Game Event Listener готова")
    
    def process_kill_event(self, data: Dict):
        """Обработать событие убийства."""
        if self.controller.should_speak('kill'):
            self.bridge.on_kill_event(data)
    
    def process_death_event(self, data: Dict):
        """Обработать событие смерти."""
        if self.controller.should_speak('death'):
            self.bridge.on_death_event(data)
    
    def process_low_health_event(self, data: Dict):
        """Обработать событие низкого здоровья (КРИТИЧЕСКОЕ)."""
        if self.controller.should_speak('low_health'):
            self.bridge.on_low_health_event(data)
    
    def process_low_ammo_event(self, data: Dict):
        """Обработать событие мало патронов (КРИТИЧЕСКОЕ)."""
        if self.controller.should_speak('low_ammo'):
            self.bridge.on_low_ammo_event(data)
    
    def process_game_start_event(self):
        """Обработать событие начала раунда."""
        if self.controller.should_speak('game_start'):
            self.bridge.on_game_start_event()
    
    def process_round_end_event(self, team_won: bool):
        """Обработать событие конца раунда."""
        if self.controller.should_speak('round_end'):
            self.bridge.on_round_end_event(team_won)
    
    def process_custom_message(self, text: str, emotion: str = "normal"):
        """Обработать пользовательское сообщение."""
        if self.controller.should_speak('custom'):
            self.bridge.on_custom_event(text, emotion)
    
    def enable_silence(self, duration: float = 5.0):
        """Включить режим молчания."""
        self.controller.enable_silence(duration)
    
    def disable_silence(self):
        """Отключить режим молчания."""
        self.controller.disable_silence()
    
    def get_stats(self) -> Dict:
        """Получить статистику."""
        return self.controller.get_stats()
    
    def wait_for_speech(self, timeout: float = None):
        """Ждать пока IRIS заканчивает говорить."""
        self.bridge.wait_for_speech(timeout)


def main():
    """Демонстрация интеграции IRIS с событиями игры."""
    logger.info("\n" + "="*70)
    logger.info("🎮 IRIS TTS INTEGRATION - ДЕМОНСТРАЦИЯ ИНТЕГРАЦИИ С ИГРОЙ")
    logger.info("="*70 + "\n")
    
    # Создаём слушателя событий
    listener = IRISGameEventListener()
    
    logger.info("\n[DEMO] Симулирую события CS2 с речью IRIS...\n")
    
    # Начало раунда
    time.sleep(0.5)
    logger.info("🎮 [CS2] Раунд начался!")
    listener.process_game_start_event()
    listener.wait_for_speech()
    
    # Убийство
    time.sleep(1)
    logger.info("🎮 [CS2] Выстрел в голову AK-47!")
    listener.process_kill_event({
        'weapon': 'AK-47',
        'headshot': True,
        'round_kills': 1
    })
    listener.wait_for_speech()
    
    # Ещё одно убийство
    time.sleep(1)
    logger.info("🎮 [CS2] Ещё одно убийство!")
    listener.process_kill_event({
        'weapon': 'AK-47',
        'headshot': False,
        'round_kills': 2
    })
    listener.wait_for_speech()
    
    # Мало здоровья (КРИТИЧЕСКОЕ!)
    time.sleep(1)
    logger.info("🎮 [CS2] ВНИМАНИЕ! HP упало до 18!")
    listener.process_low_health_event({
        'current_health': 18,
        'armor': 20
    })
    listener.wait_for_speech()
    
    # Враг рядом - включаем молчание для сосредоточения
    time.sleep(1)
    logger.info("🎮 [CS2] ВРАГ РЯДОМ! Включаем молчание для боя...")
    listener.enable_silence(duration=10.0)
    listener.wait_for_speech()
    
    # Боевые действия...
    time.sleep(2)
    logger.info("🎮 [CS2] Убийство во время молчания!")
    listener.process_kill_event({
        'weapon': 'PISTOL',
        'headshot': False,
        'round_kills': 3  # Это не будет озвучено (молчание)
    })
    
    # Отключаем молчание
    time.sleep(1)
    listener.disable_silence()
    logger.info("🎮 [CS2] Опасность миновала, молчание отключено")
    logger.info("🎤 IRIS может говорить снова!")
    
    # Конец раунда
    time.sleep(1)
    logger.info("🎮 [CS2] Раунд закончился, команда выиграла!")
    listener.process_round_end_event(team_won=True)
    listener.wait_for_speech()
    
    # Выводим статистику
    logger.info("\n" + "="*70)
    logger.info("📊 СТАТИСТИКА IRIS:")
    logger.info("="*70)
    
    stats = listener.get_stats()
    logger.info(f"\n✅ Всего сообщений: {stats['total_messages']}")
    logger.info(f"🤐 Режим молчания: {'ДА' if stats['is_silent'] else 'НЕТ'}")
    logger.info(f"📥 Очередь пуста: {'ДА' if stats['queue_empty'] else 'НЕТ'}")
    logger.info(f"\n😊 Эмоции использованы:")
    for emotion, count in stats['emotion_distribution'].items():
        logger.info(f"  - {emotion}: {count}x")
    
    if stats['last_message']:
        logger.info(f"\n📝 Последнее сообщение: [{stats['last_message']['emotion']}] {stats['last_message']['text'][:50]}...")
    
    logger.info("\n" + "="*70)
    logger.info("✅ ИНТЕГРАЦИЯ РАБОТАЕТ! IRIS ГОТОВА К CS2!")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    main()
