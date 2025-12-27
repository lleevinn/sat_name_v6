#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_voice_bridge.py - Объединение Speech Recognition + LLM + TTS
Непрерывный диалог с IRIS 🂭🔊
"""

import logging
import sys
import os
import json
import requests
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional
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

# Импортируем наши модули
try:
    from iris_speech_recognition import IRISSpeechRecognizer
    from iris_tts_emotion import IRISTTSEngine, EmotionType
except ImportError:
    logger.warning("⚠️  Не могу загрузить модули - внести в PATH")
    from iris_ai.iris_speech_recognition import IRISSpeechRecognizer
    from iris_ai.iris_tts_emotion import IRISTTSEngine, EmotionType


class ConversationMode(Enum):
    """Моды конверсации."""
    GAME_MODE = "game"      # игровые события и команды
    CHAT_MODE = "chat"      # свободный диалог
    COMMAND_MODE = "cmd"    # команды для ос и гаме


@dataclass
class ConversationMessage:
    """Одна реплика в диалоге."""
    speaker: str  # 'user' или 'iris'
    text: str
    emotion: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class IRISVoiceBridge:
    """
    IRIS Voice Bridge - полный диалог с речью.
    
    Полный цикл:
    1. Слушаем (Vosk STT)
    2. Обрабатываем (Ollama LLM)
    3. Отвечаем (говорим голосом)
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "mistral-nemo",
        speech_model_path: str = None
    ):
        """
        Инициализация Voice Bridge.
        
        Args:
            ollama_url: URL Олламы
            model_name: Наименование модели ТЛМ
            speech_model_path: Путь к модели Vosk
        """
        logger.info("👄 Объединяю IRIS Voice Bridge...")
        
        # STT Engine
        try:
            self.recognizer = IRISSpeechRecognizer(model_path=speech_model_path)
            logger.info("✅ STT Engine готов")
        except Exception as e:
            logger.error(f"❌ Ошибка STT: {e}")
            self.recognizer = None
        
        # TTS Engine
        try:
            self.tts_engine = IRISTTSEngine()
            logger.info("✅ TTS Engine готов")
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
            self.tts_engine = None
        
        # LLM Settings
        self.ollama_url = ollama_url
        self.model_name = model_name
        
        # Конверсация
        self.conversation_history = []
        self.current_mode = ConversationMode.CHAT_MODE
        self.is_active = False
        
        logger.info("✅ IRIS Voice Bridge инициализирована")
    
    def _check_ollama(self) -> bool:
        """Check если Ollama доступна."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _get_llm_response(self, user_text: str) -> str:
        """
        Получить ответ от LLM.
        
        Args:
            user_text: Текст пользователя
            
        Returns:
            Ответ Олламы
        """
        try:
            # Препарим нсторию для LLM
            system_prompt = """You are IRIS, a female gaming assistant for CS2. 
            You are helpful, friendly, and respond in Russian. Keep answers short (1-2 sentences)."""
            
            context = "\n".join([f"{msg.speaker}: {msg.text}" for msg in self.conversation_history[-5:]])
            
            prompt = f"""{context}
user: {user_text}
iris: """
            
            # Ollama API call
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                return answer if answer else "Не поняла..."
            else:
                logger.error(f"❌ Ollama error: {response.status_code}")
                return "Ошибка сервера"
        
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ollama не доступна - запусти Ollama")
            return "Оллама не работает..."
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {e}")
            return "Ошибка процесса"
    
    def _detect_emotion(self, text: str) -> str:
        """
        Определить эмоцию ответа.
        
        Args:
            text: Текст ответа
            
        Returns:
            Наименование эмоции
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['эксцитинг', 'окс', 'вуав', 'экс', '!', '!!!']):
            return 'excited'
        elif any(word in text_lower for word in ['опасно', 'КРИТ', 'урто', 'уход']):
            return 'urgent'
        elif any(word in text_lower for word in ['вернулся', 'принимаю']):
            return 'calm'
        else:
            return 'normal'
    
    def listen_and_respond(self, timeout: float = 10.0):
        """
        Один цикл диалога:
        1. слушаем
        2. обрабатываем
        3. отвечаем
        
        Args:
            timeout: Максимум время ожидания речи
        """
        if not self.recognizer:
            logger.error("❌ STT не активен")
            return
        
        if not self.tts_engine:
            logger.error("❌ TTS не активен")
            return
        
        # 1. Слушаем
        logger.info("🎙️  Слушаю...")
        self.recognizer.start_listening()
        user_text = self.recognizer.listen_once(timeout=timeout)
        self.recognizer.stop_listening()
        
        if not user_text:
            logger.warning("⚠️  Ничего не распознано")
            return
        
        logger.info(f"👤 [ВЫ]: {user_text}")
        
        # Сохраняем в историю
        self.conversation_history.append(
            ConversationMessage(speaker='user', text=user_text)
        )
        
        # 2. Обрабатываем (LLM)
        logger.info("🧠  Обработка...")
        response_text = self._get_llm_response(user_text)
        
        # 3. Отвечаем
        emotion_name = self._detect_emotion(response_text)
        emotion = getattr(EmotionType, emotion_name.upper(), EmotionType.NORMAL)
        
        logger.info(f"👅 [IRIS]: {response_text}")
        self.tts_engine.say(response_text, emotion=emotion, priority=5)
        self.tts_engine.wait_for_speech(timeout=15.0)
        
        # Сохраняем в историю
        self.conversation_history.append(
            ConversationMessage(speaker='iris', text=response_text, emotion=emotion_name)
        )
    
    def interactive_mode(self, num_exchanges: int = 5):
        """
        Интерактивный режим - несколько экспортов.
        
        Args:
            num_exchanges: Количество экспортов
        """
        logger.info("\n" + "="*70)
        logger.info(f"🂭 НАЧИНАЕМ диалог ({num_exchanges} экспортов)")
        logger.info("="*70)
        
        if not self._check_ollama():
            logger.error("\n❌ Ollama не работает! Запусти: ollama run mistral-nemo")
            return
        
        # Привет
        welcome = "Привет! Я IRIS, твоя гаминг ассистентка. Давай чатить!"
        logger.info(f"\n👅 [IRIS]: {welcome}")
        self.tts_engine.say(welcome, emotion=EmotionType.EXCITED, priority=1)
        self.tts_engine.wait_for_speech(timeout=10.0)
        
        # Начинаем экспорты
        for i in range(num_exchanges):
            logger.info(f"\n[Экспорт {i+1}/{num_exchanges}]")
            
            try:
                self.listen_and_respond(timeout=10.0)
            except KeyboardInterrupt:
                logger.info("\n🚫 На авидсвидание!")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в экспорте: {e}")
            
            time.sleep(0.5)
        
        # Итоги
        logger.info("\n" + "="*70)
        logger.info("✅ ДИАЛОГ ЗАВЕРШЕН!")
        logger.info("="*70)
        
        # Оцистка
        self.cleanup()
    
    def cleanup(self):
        """Очистить ресурсы."""
        if self.recognizer:
            self.recognizer.cleanup()
        logger.info("🧹 Очистка завершена")


def main():
    """Настоящие тесты - Voice Bridge!"""
    logger.info("\n" + "="*70)
    logger.info("🂭 IRIS VOICE BRIDGE - ПОЛНЫЙ ДИАЛОГ")
    logger.info("="*70 + "\n")
    
    # Конфигурация
    bridge = IRISVoiceBridge(
        ollama_url="http://localhost:11434",
        model_name="mistral-nemo",  # или другая модель
        speech_model_path=None  # автосеарч
    )
    
    try:
        # Интерактивные экспорты
        bridge.interactive_mode(num_exchanges=5)
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
