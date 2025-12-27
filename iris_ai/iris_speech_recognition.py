#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_speech_recognition.py - Распознавание речи (STT) с помощью Vosk
Русский язык + real-time обработка 🎤📝
"""

import logging
import sys
import os
import json
import threading
from pathlib import Path
from vosk import Model, KaldiRecognizer
import pyaudio
import queue

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


class IRISSpeechRecognizer:
    """
    IRIS Speech Recognition Engine - распознавание русской речи.
    
    Использует Vosk для offline распознавания:
    - Не требует интернета
    - Работает в real-time
    - Поддерживает русский язык (vosk-model-ru-0.22)
    """
    
    def __init__(self, model_path: str = None):
        """
        Инициализация распознавателя.
        
        Args:
            model_path: Путь к Vosk модели (по умолчанию ищет в models/)
        """
        # Поиск модели
        if model_path is None:
            base_path = Path(__file__).parent.parent / "models" / "vosk-model-ru-0.22"
            if not base_path.exists():
                raise FileNotFoundError(
                    f"❌ Модель не найдена: {base_path}\n"
                    f"Скачай с https://github.com/alphacep/vosk-models/releases\n"
                    f"Распакуй в: C:\\Users\\Ghost\\Desktop\\iris_ai\\models\\"
                )
            model_path = str(base_path)
        
        logger.info(f"🎤 Загружаю модель Vosk: {model_path}")
        self.model = Model(model_path)
        
        # Инициализация PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recognizer = None
        
        # Очередь результатов
        self.results_queue = queue.Queue()
        self.is_listening = False
        
        # Буфер для partial результатов
        self.partial_results = []
        self.last_final_result = None
        
        logger.info("✅ IRIS Speech Recognizer инициализирован")
    
    def start_listening(self):
        """Запустить прослушивание микрофона."""
        if self.is_listening:
            logger.warning("⚠️  Уже слушаем микрофон!")
            return
        
        try:
            # Создаём поток для прослушивания
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096
            )
            
            self.recognizer = KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords("")  # Пусто - слушаем всё
            
            self.is_listening = True
            
            # Запускаем worker поток
            self.listener_thread = threading.Thread(
                target=self._listen_worker,
                daemon=True
            )
            self.listener_thread.start()
            
            logger.info("🎙️  Микрофон активирован - слушаю русскую речь...")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при включении микрофона: {e}")
            self.is_listening = False
    
    def stop_listening(self):
        """Остановить прослушивание."""
        self.is_listening = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        self.recognizer = None
        logger.info("🔇 Микрофон отключен")
    
    def _parse_vosk_result(self, json_str: str, is_partial: bool = False) -> str:
        """
        Парсим JSON результат от Vosk.
        
        Args:
            json_str: JSON строка от Vosk
            is_partial: Это partial или final результат?
            
        Returns:
            Распознанный текст
        """
        try:
            data = json.loads(json_str)
            
            # Для final результатов
            if not is_partial and 'result' in data:
                words = data['result']
                if isinstance(words, list) and len(words) > 0:
                    # Vosk возвращает список словарей с ключом 'conf'
                    text = ' '.join([word.get('conf', '') for word in words if isinstance(word, dict)])
                    return text.strip()
            
            # Для partial результатов
            if is_partial and 'partial' in data:
                partial = data['partial']
                if isinstance(partial, str):
                    return partial.strip()
            
            return ""
        
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️  Ошибка парсинга JSON: {e}")
            return ""
        except Exception as e:
            logger.debug(f"⚠️  Ошибка при парсинге результата: {e}")
            return ""
    
    def _listen_worker(self):
        """Worker поток для непрерывного прослушивания."""
        logger.info("🔴 WORKER: Начинаю слушать...")
        
        while self.is_listening:
            try:
                # Читаем данные с микрофона
                data = self.stream.read(4096, exception_on_overflow=False)
                
                # Проверяем AcceptWaveform (это говорит готов ли результат)
                if self.recognizer.AcceptWaveform(data):
                    # Финальный результат готов!
                    result_json = self.recognizer.Result()
                    text = self._parse_vosk_result(result_json, is_partial=False)
                    
                    if text:
                        logger.info(f"✅ [РАСПОЗНАНО] {text}")
                        self.last_final_result = text
                        self.results_queue.put({'type': 'final', 'text': text})
                
                else:
                    # Partial результат - слово ещё не закончилось
                    try:
                        result_json = self.recognizer.PartialResult()
                        text = self._parse_vosk_result(result_json, is_partial=True)
                        
                        if text and text != self.partial_results[-1:][0] if self.partial_results else False:
                            logger.debug(f"📝 [PARTIAL] {text}")
                            self.partial_results.append(text)
                    
                    except AttributeError:
                        # PartialResult может не быть в некоторых версиях Vosk
                        logger.debug("⚠️  PartialResult недоступен, пропускаю")
                        continue
                    except Exception as e:
                        logger.debug(f"⚠️  Ошибка partial: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"❌ Ошибка в listen_worker: {e}")
                self.is_listening = False
                break
        
        logger.info("🔴 WORKER: Остановлен")
    
    def get_last_result(self, timeout: float = 5.0) -> str:
        """
        Получить последний распознанный текст.
        
        Args:
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            Распознанный текст или пустая строка
        """
        try:
            result = self.results_queue.get(timeout=timeout)
            
            if result['type'] == 'final':
                return result['text']
            
        except queue.Empty:
            logger.warning(f"⏱️  Timeout ожидания результата ({timeout}s)")
        
        return ""
    
    def listen_once(self, timeout: float = 10.0) -> str:
        """
        Слушать один раз и вернуть результат.
        
        Args:
            timeout: Максимальное время ожидания
            
        Returns:
            Распознанный текст
        """
        # Очищаем очередь
        while not self.results_queue.empty():
            try:
                self.results_queue.get_nowait()
            except queue.Empty:
                break
        
        # Ждём финального результата
        import time
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    result = self.results_queue.get(timeout=0.1)
                    
                    if result['type'] == 'final':
                        text = result['text']
                        logger.info(f"🎯 [FINAL] {text}")
                        return text
                
                except queue.Empty:
                    continue
        
        except Exception as e:
            logger.error(f"❌ Ошибка listen_once: {e}")
        
        # Timeout - вернём последний результат если есть
        if self.last_final_result:
            return self.last_final_result
        
        return ""
    
    def get_context(self) -> dict:
        """Получить контекст распознавания."""
        return {
            'is_listening': self.is_listening,
            'last_result': self.last_final_result,
            'model': str(self.model),
        }
    
    def cleanup(self):
        """Очистить ресурсы."""
        self.stop_listening()
        if self.stream:
            self.stream.close()
        self.audio.terminate()
        logger.info("🧹 Ресурсы очищены")


def main():
    """Тестирование Speech Recognizer."""
    logger.info("\n" + "="*70)
    logger.info("🎤 IRIS SPEECH RECOGNITION - ДЕМОНСТРАЦИЯ")
    logger.info("="*70 + "\n")
    
    try:
        # Инициализируем
        recognizer = IRISSpeechRecognizer()
        
        # Запускаем прослушивание
        recognizer.start_listening()
        
        logger.info("\n📢 Говори на русском! (максимум 10 сек)\n")
        
        # Слушаем
        text = recognizer.listen_once(timeout=10.0)
        
        if text:
            logger.info(f"\n✅ ВЫ СКАЗАЛИ: '{text}'")
        else:
            logger.warning("\n⚠️  Речь не распознана")
        
        # Очищаем
        recognizer.cleanup()
        
        logger.info("\n" + "="*70)
        logger.info("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        logger.info("="*70 + "\n")
    
    except FileNotFoundError as e:
        logger.error(f"\n❌ {e}")
    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
