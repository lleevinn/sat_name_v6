#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_text_input_demo.py - IRIS диалог с текстовым вводом (БЕЗ микрофона)
Перфектно для тестирования LLM + TTS! 🎤✨
"""

import logging
import sys
import os
import requests
import time
from typing import Optional

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
    from iris_tts_emotion import IRISTTSEngine, EmotionType
except ImportError:
    logger.warning("⚠️  Не могу загрузить модули - внести в PATH")
    from iris_ai.iris_tts_emotion import IRISTTSEngine, EmotionType


class IRISTextDialogDemo:
    """
    IRIS Text Dialog - диалог с текстовым вводом.
    
    Полный цикл:
    1. Пользователь вводит текст
    2. Ollama обрабатывает (LLM)
    3. IRIS отвечает голосом (TTS)
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen3:4b-instruct"
    ):
        """
        Инициализация.
        
        Args:
            ollama_url: URL Оллама
            model_name: Название модели ТЛМ
        """
        logger.info("🎙️  Инициализирую IRIS Text Dialog...")
        
        # TTS Engine
        try:
            self.tts_engine = IRISTTSEngine()
            logger.info("✅ TTS Engine готов")
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
            raise
        
        # LLM Settings
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.conversation_history = []
        
        logger.info(f"✅ IRIS Text Dialog инициализирована (модель: {model_name})")
    
    def _check_ollama(self) -> bool:
        """Проверить доступность Ollama."""
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
            Ответ Оллама
        """
        try:
            # Подготавливаем контекст из истории
            context = "\n".join([f"{msg['speaker']}: {msg['text']}" for msg in self.conversation_history[-5:]])
            
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
            logger.error("❌ Ollama не доступна - запусти Ollama!")
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
            Название эмоции
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
    
    def interactive_dialog(self):
        """
        Интерактивный диалог с текстовым вводом.
        """
        logger.info("\n" + "="*70)
        logger.info("💬 IRIS TEXT DIALOG - ИНТЕРАКТИВНЫЙ РЕЖИМ")
        logger.info("="*70)
        
        if not self._check_ollama():
            logger.error(f"\n❌ Ollama не работает! Запусти: ollama run {self.model_name}")
            return
        
        # Приветствие
        welcome = "Привет! Я IRIS, твоя гейминг ассистентка. О чём хочешь поговорить?"
        logger.info(f"\n👩 [IRIS]: {welcome}")
        self.tts_engine.say(welcome, emotion=EmotionType.EXCITED, priority=1)
        self.tts_engine.wait_for_speech(timeout=10.0)
        
        # Добавляем в историю
        self.conversation_history.append({'speaker': 'iris', 'text': welcome})
        
        # Основной цикл диалога
        while True:
            try:
                # Получаем ввод пользователя
                logger.info("\n" + "-"*70)
                user_input = input("\n🎤 [ВЫ]: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['выход', 'exit', 'quit', 'q']:
                    logger.info("\n👋 На свидание!")
                    self.tts_engine.say("На свидание!", emotion=EmotionType.CALM, priority=5)
                    self.tts_engine.wait_for_speech(timeout=5.0)
                    break
                
                logger.info(f"📝 Вы сказали: '{user_input}'")
                
                # Добавляем в историю
                self.conversation_history.append({'speaker': 'user', 'text': user_input})
                
                # Получаем ответ от LLM
                logger.info("🧠 Обработка...")
                response_text = self._get_llm_response(user_input)
                
                # Определяем эмоцию
                emotion_name = self._detect_emotion(response_text)
                emotion = getattr(EmotionType, emotion_name.upper(), EmotionType.NORMAL)
                
                # Выводим и озвучиваем ответ
                logger.info(f"\n👩 [IRIS]: {response_text}")
                self.tts_engine.say(response_text, emotion=emotion, priority=5)
                self.tts_engine.wait_for_speech(timeout=15.0)
                
                # Добавляем в историю
                self.conversation_history.append({'speaker': 'iris', 'text': response_text})
            
            except KeyboardInterrupt:
                logger.info("\n🛑 Диалог прерван...")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в диалоге: {e}")
                continue
        
        # Итоги
        logger.info("\n" + "="*70)
        logger.info("✅ ДИАЛОГ ЗАВЕРШЁН!")
        logger.info("="*70)
        logger.info(f"\n📊 Всего сообщений: {len(self.conversation_history)}")
    
    def cleanup(self):
        """Очистить ресурсы."""
        logger.info("🧹 Очистка...")


def main():
    """Главная функция."""
    logger.info("\n" + "="*70)
    logger.info("🌟 IRIS TEXT DIALOG DEMO")
    logger.info("="*70 + "\n")
    
    try:
        # Создаём диалог
        dialog = IRISTextDialogDemo(
            ollama_url="http://localhost:11434",
            model_name="qwen3:4b-instruct"
        )
        
        # Запускаем интерактивный режим
        dialog.interactive_dialog()
        
        # Очищаем
        dialog.cleanup()
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
