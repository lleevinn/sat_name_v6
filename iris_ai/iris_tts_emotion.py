#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_tts_emotion.py - IRIS с женским голосом, эмоциями и живым диалогом
Это JARVIS для CS2! 🔊✨

Features:
- Женский голос (бархатный, нежный, приятный)
- 6 эмоций с разной интонацией
- Приоритетная очередь для критических событий
- Асинхронная обработка (не блокирует игру)
- Контекстная память разговора
- Интеграция с игровыми событиями
"""

import logging
import sys
import os
import pyttsx3
import threading
import queue
import json
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List
import time

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


class EmotionType(Enum):
    """Эмоции IRIS - каждая имеет свой тон голоса."""
    CALM = {"rate": 150, "volume": 0.8}  # Спокойная - медленная, тихая
    NORMAL = {"rate": 170, "volume": 0.85}  # Обычная - стандартная скорость
    EXCITED = {"rate": 200, "volume": 0.95}  # Восторженная - быстрая, громкая
    URGENT = {"rate": 220, "volume": 1.0}  # КРИТИЧЕСКАЯ! - максимально быстрая и громкая
    WORRIED = {"rate": 140, "volume": 0.75}  # Озабоченная - медленная, тихая, грустная
    FLIRTY = {"rate": 160, "volume": 0.9}  # Заигрывающая - мягкая, игривая


@dataclass
class SpeechEvent:
    """Событие для произнесения."""
    text: str
    emotion: EmotionType = EmotionType.NORMAL
    priority: int = 5
    event_type: str = "normal"
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def __lt__(self, other):
        """Сравнение для приоритетной очереди."""
        return self.priority < other.priority


class IRISTTSEngine:
    """
    IRIS TTS Engine - женский голос с эмоциями.
    
    Это основной модуль для озвучивания IRIS в реальном времени.
    Поддерживает:
    - Женский голос (бархатный)
    - 6 эмоциональных состояний
    - Приоритетную обработку событий
    - Контекстную память разговора
    """
    
    def __init__(self, voice_id: int = None):
        """
        Инициализация TTS и эмоционального движка.
        
        Args:
            voice_id: ID голоса (если None, ищет женский автоматически)
        """
        self.engine = pyttsx3.init()
        self._setup_voice(voice_id)
        
        self.speech_queue = queue.PriorityQueue()
        self.is_speaking = False
        self.current_speech_event = None
        self.speech_done_event = threading.Event()
        self.speech_done_event.set()  # Изначально готово
        
        # Контекст разговора и игры
        self.context = {
            "last_event": None,
            "game_state": {},
            "conversation_history": [],
            "emotion_distribution": {}
        }
        
        # Запускаем worker thread
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()
        
        logger.info("✅ IRIS TTS Engine инициализирована")
    
    def _setup_voice(self, voice_id: int = None):
        """
        Настройка женского голоса.
        
        Args:
            voice_id: ID голоса (если None, ищет женский автоматически)
        """
        voices = self.engine.getProperty('voices')
        
        if voice_id is not None:
            self.engine.setProperty('voice', voices[voice_id].id)
            logger.info(f"🎀 Голос установлен (ID: {voice_id}): {voices[voice_id].name}")
        else:
            # Поиск женского голоса
            female_voice = None
            for i, voice in enumerate(voices):
                voice_name_lower = voice.name.lower()
                if 'female' in voice_name_lower or 'woman' in voice_name_lower or 'zira' in voice_name_lower:
                    female_voice = voice.id
                    logger.info(f"🎀 Найден женский голос: {voice.name} (ID: {i})")
                    break
            
            if female_voice:
                self.engine.setProperty('voice', female_voice)
            else:
                logger.warning("⚠️  Женский голос не найден, используется голос по умолчанию")
        
        # Дефолтные настройки
        self.engine.setProperty('rate', 170)  # Скорость речи
        self.engine.setProperty('volume', 0.9)  # Громкость
    
    def _speech_worker(self):
        """Worker поток для обработки очереди речи."""
        while True:
            try:
                priority, speech_event = self.speech_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            self._speak_with_emotion(speech_event)
    
    def _speak_with_emotion(self, event: SpeechEvent):
        """
        Говорить с эмоциями.
        
        Args:
            event: SpeechEvent с текстом и эмоцией
        """
        try:
            self.speech_done_event.clear()
            self.is_speaking = True
            self.current_speech_event = event
            emotion = event.emotion.value
            emotion_name = event.emotion.name
            
            # Применяем эмоциональные параметры
            self.engine.setProperty('rate', emotion['rate'])
            self.engine.setProperty('volume', emotion['volume'])
            
            # Логируем начало речи
            logger.info(f"🔊 [{emotion_name}] {event.text[:60]}...")
            
            # Говорим!
            self.engine.say(event.text)
            self.engine.runAndWait()
            
            # Сохраняем в историю
            self.context['conversation_history'].append({
                'speaker': 'iris',
                'text': event.text,
                'emotion': emotion_name,
                'event_type': event.event_type,
                'timestamp': time.time()
            })
            
            # Обновляем статистику эмоций
            if emotion_name not in self.context['emotion_distribution']:
                self.context['emotion_distribution'][emotion_name] = 0
            self.context['emotion_distribution'][emotion_name] += 1
            
            # Логируем успешное произнесение
            logger.info(f"✅ [IRIS_SAY] {event.text}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
        finally:
            self.is_speaking = False
            self.current_speech_event = None
            self.speech_done_event.set()
    
    def say(self, text: str, emotion: EmotionType = EmotionType.NORMAL, 
            priority: int = 5, event_type: str = "normal"):
        """
        Добавить текст в очередь для произнесения.
        
        Args:
            text: Текст для произнесения
            emotion: Эмоция (по умолчанию NORMAL)
            priority: Приоритет в очереди (1 - максимальный, 10 - минимальный)
            event_type: Тип события (для логирования)
        """
        event = SpeechEvent(text=text, emotion=emotion, priority=priority, event_type=event_type)
        self.speech_queue.put((priority, event))
        logger.info(f"📤 В очередь: [{emotion.name}] {text[:40]}... (приоритет: {priority})")
    
    def init_sound(self):
        """Звук инициализации (как JARVIS при запуске)."""
        logger.info("\n" + "="*70)
        logger.info("🌟 IRIS ИНИЦИАЛИЗИРУЕТСЯ...")
        logger.info("="*70)
        
        # Эффект включения с женским голосом
        self.say(
            "IRIS онлайн. Все системы в норме. Я готова. Давайте начнём.",
            emotion=EmotionType.CALM,
            priority=1,
            event_type="init"
        )
        time.sleep(0.5)
    
    # ==================== ИГРОВЫЕ СОБЫТИЯ ====================
    
    def on_kill(self, data: dict):
        """
        Реакция на убийство врага.
        
        Args:
            data: {weapon, headshot, round_kills}
        """
        weapon = data.get('weapon', 'неизвестное оружие')
        headshot = data.get('headshot', False)
        round_kills = data.get('round_kills', 1)
        
        if round_kills == 1:
            if headshot:
                responses = [
                    f"Снайпер! Идеальный выстрел в голову!",
                    f"Headshot! Отличная точность!",
                    f"Голова - взята! Так держать!",
                ]
            else:
                responses = [
                    f"Хорошо! Враг нейтрализован.",
                    f"Одно убийство. Так держать!",
                    f"Красиво! Продолжай в том же духе!",
                ]
            emotion = EmotionType.EXCITED
            priority = 5
        
        elif round_kills == 2:
            responses = [
                "Двойное убийство! Ты в форме!",
                "Два врага down! Продолжай в том же духе!",
                "Double kill! Охотница показала класс!",
            ]
            emotion = EmotionType.EXCITED
            priority = 4
        
        elif round_kills == 3:
            responses = [
                "ТРОЙНОЕ УБИЙСТВО! Ты легенда!",
                "Три врага повержено! Просто чудо!",
                "Triple kill! Ты неостановима!",
            ]
            emotion = EmotionType.EXCITED
            priority = 3
        
        else:
            responses = [
                f"Уже {round_kills} убийств! Ты машина смерти!",
                f"{round_kills} врагов! Это невероятно!",
                f"Квадро-килл! Ты просто королева!",
            ]
            emotion = EmotionType.EXCITED
            priority = 2
        
        text = responses[round_kills % len(responses)]
        self.say(text, emotion=emotion, priority=priority, event_type="kill")
    
    def on_low_health(self, data: dict):
        """
        КРИТИЧЕСКОЕ: Мало здоровья!
        
        Args:
            data: {current_health, armor}
        """
        hp = data.get('current_health', 0)
        armor = data.get('armor', 0)
        
        if hp <= 10:
            text = f"Критическое! {hp} HP! Укройся немедленно!"
            emotion = EmotionType.URGENT
            priority = 1
        elif hp <= 25:
            text = f"Осторожнее! {hp} жизни! Найди укрытие!"
            emotion = EmotionType.WORRIED
            priority = 2
        else:
            text = f"Здоровье падает, {hp} HP. Будь осторожнее."
            emotion = EmotionType.NORMAL
            priority = 3
        
        self.say(text, emotion=emotion, priority=priority, event_type="low_health")
    
    def on_low_ammo(self, data: dict):
        """
        КРИТИЧЕСКОЕ: Мало патронов!
        
        Args:
            data: {weapon, ammo_magazine}
        """
        weapon = data.get('weapon', 'оружие')
        ammo = data.get('ammo_magazine', 0)
        
        if ammo <= 3:
            text = f"Боеприпасы! Смени магазин или оружие!"
            emotion = EmotionType.URGENT
            priority = 1
        elif ammo <= 10:
            text = f"Мало патронов в магазине. Будь экономнее."
            emotion = EmotionType.WORRIED
            priority = 2
        else:
            text = f"Запас боеприпасов заканчивается."
            emotion = EmotionType.NORMAL
            priority = 3
        
        self.say(text, emotion=emotion, priority=priority, event_type="low_ammo")
    
    def on_death(self, data: dict):
        """
        Реакция на смерть игрока - поддержка.
        
        Args:
            data: {kd_ratio, total_deaths}
        """
        kd = data.get('kd_ratio', 0)
        
        if kd > 2.0:
            responses = [
                "Отличный KD! Ты играешь как профи. Продолжай!",
                "С таким KD ты скоро будешь королевой сервера!",
                "Даже легенды умирают. Вернёшься ещё сильнее!",
            ]
            emotion = EmotionType.EXCITED
        elif kd > 1.0:
            responses = [
                "Хороший KD! Следующий раунд будет ещё лучше!",
                "Ты учишься быстро. Возьмём реванш!",
                "Хороший результат. Давай пробуем снова!",
            ]
            emotion = EmotionType.CALM
        else:
            responses = [
                "Не печалься! Это всё опыт и обучение!",
                "Каждая смерть - это урок. Вперёд к победе!",
                "Ты растёшь и учишься. Скоро будешь лучше!",
            ]
            emotion = EmotionType.CALM
        
        text = responses[int(kd) % len(responses)]
        self.say(text, emotion=emotion, priority=4, event_type="death")
    
    def on_game_start(self):
        """Реакция на начало раунда."""
        responses = [
            "Новый раунд! Покажи им кто королева!",
            "Раунд начался! Сосредоточься и побеждай!",
            "Пора в бой, охотница!",
            "Раунд запущен. Удачи!",
        ]
        text = responses[int(time.time()) % len(responses)]
        self.say(text, emotion=EmotionType.EXCITED, priority=5, event_type="game_start")
    
    def on_round_end(self, team_won: bool):
        """
        Реакция на конец раунда.
        
        Args:
            team_won: True если команда выиграла раунд
        """
        if team_won:
            responses = [
                "Раунд выигран! Отличная работа, королева!",
                "Победа! Ты сыграла как профессионал!",
                "Выиграли раунд! Продолжай в том же духе!",
            ]
            emotion = EmotionType.EXCITED
        else:
            responses = [
                "Раунд проигран. Но мы вернёмся сильнее!",
                "Не переживай, следующий раунд будет наш!",
                "Упали в этом раунде, но вернёмся!",
            ]
            emotion = EmotionType.CALM
        
        text = responses[int(time.time()) % len(responses)]
        self.say(text, emotion=emotion, priority=5, event_type="round_end")
    
    def on_custom_message(self, text: str, emotion_name: str = "normal"):
        """
        Кастомное сообщение с выбранной эмоцией.
        
        Args:
            text: Текст для произнесения
            emotion_name: Имя эмоции (calm, normal, excited, urgent, worried, flirty)
        """
        emotion_map = {
            'calm': EmotionType.CALM,
            'normal': EmotionType.NORMAL,
            'excited': EmotionType.EXCITED,
            'urgent': EmotionType.URGENT,
            'worried': EmotionType.WORRIED,
            'flirty': EmotionType.FLIRTY,
        }
        emotion = emotion_map.get(emotion_name.lower(), EmotionType.NORMAL)
        self.say(text, emotion=emotion, priority=5, event_type="custom")
    
    # ==================== УТИЛИТЫ ====================
    
    def get_context(self) -> Dict:
        """Получить контекст разговора и состояние игры."""
        return self.context
    
    def get_conversation_history(self) -> List[Dict]:
        """Получить историю разговора."""
        return self.context['conversation_history']
    
    def get_emotions_stats(self) -> Dict:
        """Получить статистику использования эмоций."""
        return self.context['emotion_distribution']
    
    def is_queue_empty(self) -> bool:
        """Проверить пуста ли очередь речи."""
        return self.speech_queue.empty()
    
    def wait_for_speech(self, timeout: float = 10.0):
        """
        Ждать пока IRIS заканчивает говорить.
        
        Args:
            timeout: Максимальное время ожидания в секундах (по умолчанию 10)
        """
        # Ждём с большим timeout'ом, потому что pyttsx3 на Windows может быть медленным
        if not self.speech_done_event.wait(timeout=timeout):
            logger.warning(f"⏱️  Timeout при ожидании окончания речи ({timeout}s)")
    
    def clear_queue(self):
        """Очистить очередь речи."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("🗑️  Очередь речи очищена")


def main():
    """Тестирование TTS Engine."""
    logger.info("\n" + "="*70)
    logger.info("🎤 IRIS TTS EMOTION ENGINE - ПОЛНАЯ ДЕМОНСТРАЦИЯ")
    logger.info("="*70 + "\n")
    
    iris = IRISTTSEngine()
    
    # Инициализация с звуком (как JARVIS)
    iris.init_sound()
    iris.wait_for_speech(timeout=8.0)
    
    # Тестируем различные события
    logger.info("\n[TEST] Симулирую события игры...\n")
    
    # 1. Начало раунда
    time.sleep(0.5)
    iris.on_game_start()
    iris.wait_for_speech(timeout=5.0)
    
    # 2. Убийство
    time.sleep(0.5)
    iris.on_kill({'weapon': 'AWP', 'headshot': True, 'round_kills': 1})
    iris.wait_for_speech(timeout=5.0)
    
    # 3. Двойное убийство
    time.sleep(0.5)
    iris.on_kill({'weapon': 'AK-47', 'headshot': False, 'round_kills': 2})
    iris.wait_for_speech(timeout=5.0)
    
    # 4. Мало здоровья (КРИТИЧЕСКОЕ!)
    time.sleep(0.5)
    iris.on_low_health({'current_health': 15, 'armor': 25})
    iris.wait_for_speech(timeout=5.0)
    
    # 5. Мало патронов (КРИТИЧЕСКОЕ!)
    time.sleep(0.5)
    iris.on_low_ammo({'weapon': 'AK-47', 'ammo_magazine': 2})
    iris.wait_for_speech(timeout=5.0)
    
    # 6. Смерть
    time.sleep(0.5)
    iris.on_death({'kd_ratio': 1.5})
    iris.wait_for_speech(timeout=5.0)
    
    # 7. Конец раунда (победа)
    time.sleep(0.5)
    iris.on_round_end(team_won=True)
    iris.wait_for_speech(timeout=5.0)
    
    # 8. Кастомное сообщение с флиртом
    time.sleep(0.5)
    iris.on_custom_message(
        "Ты просто королева! Никто не может с тобой сравниться!",
        emotion_name='flirty'
    )
    iris.wait_for_speech(timeout=5.0)
    
    # Выводим статистику
    logger.info("\n" + "="*70)
    logger.info("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    logger.info("="*70)
    
    context = iris.get_context()
    logger.info(f"\n📊 СТАТИСТИКА:")
    logger.info(f"  Всего реплик: {len(context['conversation_history'])}")
    logger.info(f"  Использовано эмоций: {iris.get_emotions_stats()}")
    
    logger.info(f"\n💬 ИСТОРИЯ РАЗГОВОРА:")
    for i, msg in enumerate(context['conversation_history'], 1):
        logger.info(f"  {i}. [{msg['emotion']}] {msg['text'][:60]}...")
    
    logger.info("\n" + "="*70)
    logger.info("🔊 Готово! IRIS готова к CS2!")
    logger.info("="*70 + "\n")


if __name__ == "__main__":
    main()
