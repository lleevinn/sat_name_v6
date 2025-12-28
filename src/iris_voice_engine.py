"""
IRIS VOICE ENGINE - Живой аудиовызов
Реальное время: микрофон → речь → LLM → голос → динамики
С прерыванием и естественной речью
Версия: 2.0
Автор: Ghost
"""

import os
import sys
import threading
import queue
import time
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import json

try:
    import pyaudio
    import wave
    import numpy as np
except ImportError:
    print("Установите: pip install pyaudio numpy")
    pyaudio = None
    wave = None
    np = None

try:
    import pyttsx3
except ImportError:
    print("Установите: pip install pyttsx3")
    pyttsx3 = None

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("Установите: pip install vosk")
    from vosk import None as vosk_unavailable
    vosk_unavailable = True

# ===================== НАСТРОЙКА ЛОГИРОВАНИЯ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iris_voice_engine.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('IrisVoiceEngine')


# ===================== ГОЛОСОВОЕ РАСПОЗНАВАНИЕ =====================
class VoiceRecognizer:
    """Распознавание речи в реальном времени (Vosk + русский)"""
    
    def __init__(self, model_path: str = None):
        """Инициализация распознавателя"""
        self.model_path = model_path or os.getenv('VOSK_MODEL_RU', 'model_ru')
        self.model = None
        self.is_listening = False
        self.recognizer = None
        self.audio_interface = None
        
        self._init_model()
    
    def _init_model(self):
        """Инициализация модели Vosk"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Модель не найдена: {self.model_path}")
                logger.info("Используется эмуляция распознавания")
                self.model = None
                return
            
            from vosk import Model, KaldiRecognizer
            self.model = Model(self.model_path)
            logger.info(f"Модель загружена: {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            logger.info("Используется эмуляция распознавания")
            self.model = None
    
    def start_listening(self, on_text: Callable[[str], None]) -> threading.Thread:
        """Запуск слушания микрофона"""
        if not pyaudio:
            logger.error("PyAudio недоступен")
            return None
        
        self.is_listening = True
        
        # Запуск слушания в отдельном потоке
        thread = threading.Thread(target=self._listen_loop, args=(on_text,), daemon=True)
        thread.start()
        
        logger.info("Слушание микрофона запущено")
        return thread
    
    def _listen_loop(self, on_text: Callable[[str], None]):
        """Основной цикл слушания"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096
            )
            
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self.model, 16000)
            rec.SetWords([
                "убийство", "смерть", "раунд", "карта", "экономика",
                "стратегия", "позиция", "враг", "команда", "бомба",
                "привет", "как дела", "спасибо", "ирис", "ириска"
            ])
            
            logger.info("Слушание активно...")
            
            while self.is_listening:
                try:
                    data = stream.read(4096, exception_on_overflow=False)
                    
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if 'result' in result:
                            text = ' '.join([item['conf'] for item in result['result']])
                            if text and len(text.strip()) > 0:
                                logger.debug(f"Распознано: {text}")
                                on_text(text)
                except Exception as e:
                    logger.error(f"Ошибка обработки аудио: {e}")
                    continue
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            logger.error(f"Ошибка в цикле слушания: {e}")
    
    def stop_listening(self):
        """Остановка слушания"""
        self.is_listening = False
        logger.info("Слушание остановлено")
    
    def simulate_text(self, text: str) -> str:
        """Эмуляция распознавания (для тестирования)"""
        logger.debug(f"[ЭМУЛЯЦИЯ] Распознано: {text}")
        return text


# ===================== СИНТЕЗ РЕЧИ (TTS) =====================
class VoiceSynthesizer:
    """Синтез речи в реальном времени (TTS)"""
    
    def __init__(self, voice_speed: float = 1.0, voice_volume: float = 0.9):
        """Инициализация синтезатора"""
        self.engine = None
        self.voice_speed = voice_speed
        self.voice_volume = voice_volume
        self.is_speaking = False
        
        self._init_engine()
    
    def _init_engine(self):
        """Инициализация TTS движка"""
        try:
            if not pyttsx3:
                logger.error("pyttsx3 недоступен")
                return
            
            self.engine = pyttsx3.init()
            
            # Установка голоса (русский, женский)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'russian' in voice.languages or 'ru' in str(voice.id).lower():
                    self.engine.setProperty('voice', voice.id)
                    logger.info(f"Голос установлен: {voice.id}")
                    break
            
            # Скорость и громкость
            self.engine.setProperty('rate', int(150 * self.voice_speed))
            self.engine.setProperty('volume', self.voice_volume)
            
            logger.info("TTS движок инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации TTS: {e}")
    
    def speak(self, text: str, interrupting: bool = False) -> bool:
        """Воспроизведение текста"""
        if not self.engine:
            logger.warning(f"[ЭМУЛЯЦИЯ] Говорю: {text}")
            return True
        
        try:
            # Если нужно прерывание - остановить текущую речь
            if interrupting and self.is_speaking:
                self.engine.stop()
                logger.debug("Предыдущая речь прервана")
            
            # Очистка от старых очередей
            self.engine.runAndWait()
            
            # Произнести текст
            self.engine.say(text)
            self.is_speaking = True
            self.engine.runAndWait()
            self.is_speaking = False
            
            logger.debug(f"Произнесено: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Ошибка синтеза: {e}")
            return False
    
    def speak_async(self, text: str, interrupting: bool = False):
        """Асинхронное воспроизведение"""
        thread = threading.Thread(
            target=self.speak,
            args=(text, interrupting),
            daemon=True
        )
        thread.start()
        return thread
    
    def stop(self):
        """Остановка воспроизведения"""
        if self.engine:
            try:
                self.engine.stop()
                self.is_speaking = False
                logger.debug("Воспроизведение остановлено")
            except Exception as e:
                logger.error(f"Ошибка остановки: {e}")


# ===================== ОСНОВНОЙ ENGINE =====================
class IrisVoiceEngine:
    """Основной голосовой engine для IRIS"""
    
    def __init__(self, 
                 llm_callback: Optional[Callable[[str], str]] = None,
                 enable_voice_input: bool = True,
                 enable_voice_output: bool = True):
        """Инициализация"""
        self.llm_callback = llm_callback
        self.enable_voice_input = enable_voice_input
        self.enable_voice_output = enable_voice_output
        
        # Компоненты
        self.recognizer = VoiceRecognizer()
        self.synthesizer = VoiceSynthesizer()
        
        # Состояние
        self.is_running = False
        self.is_listening = False
        self.current_user_text = ""
        self.last_speech_time = 0
        self.interruption_enabled = True
        
        # Очереди
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        
        # Потоки
        self.input_thread = None
        self.processing_thread = None
        self.output_thread = None
        
        # Статистика
        self.stats = {
            'total_inputs': 0,
            'total_outputs': 0,
            'start_time': time.time(),
            'last_input': None,
            'last_output': None
        }
        
        logger.info("IrisVoiceEngine инициализирован")
    
    def start(self):
        """Запуск engine"""
        if self.is_running:
            logger.warning("Engine уже запущен")
            return
        
        self.is_running = True
        logger.info("🎤 Запуск IRIS Voice Engine...")
        
        # Запуск входящего потока (микрофон)
        if self.enable_voice_input:
            self.input_thread = self.recognizer.start_listening(
                on_text=self._on_user_text
            )
        
        # Запуск обработки
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        # Запуск выхода (синтез)
        if self.enable_voice_output:
            self.output_thread = threading.Thread(
                target=self._output_loop,
                daemon=True
            )
            self.output_thread.start()
        
        logger.info("✅ Voice Engine запущен")
    
    def stop(self):
        """Остановка engine"""
        if not self.is_running:
            return
        
        logger.info("🛑 Остановка Voice Engine...")
        
        self.is_running = False
        self.recognizer.stop_listening()
        self.synthesizer.stop()
        
        # Ждём завершения потоков
        if self.input_thread:
            self.input_thread.join(timeout=2)
        if self.processing_thread:
            self.processing_thread.join(timeout=2)
        if self.output_thread:
            self.output_thread.join(timeout=2)
        
        logger.info("✅ Voice Engine остановлен")
    
    def _on_user_text(self, text: str):
        """Callback когда пользователь говорит"""
        if not text or len(text.strip()) < 2:
            return
        
        logger.info(f"👤 Пользователь: {text}")
        self.current_user_text = text
        self.stats['total_inputs'] += 1
        self.stats['last_input'] = text
        
        # Если IRIS говорит - прервать её
        if self.synthesizer.is_speaking and self.interruption_enabled:
            logger.debug("Прерывание речи IRIS...")
            self.synthesizer.stop()
            time.sleep(0.2)  # Небольшая пауза
        
        # Добавить в очередь обработки
        self.input_queue.put(text)
    
    def _processing_loop(self):
        """Основной цикл обработки"""
        while self.is_running:
            try:
                # Получить входящий текст
                try:
                    user_text = self.input_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Вызвать LLM callback
                if self.llm_callback:
                    logger.debug(f"Отправка в LLM: {user_text}")
                    iris_response = self.llm_callback(user_text)
                    
                    if iris_response:
                        logger.info(f"🌸 IRIS: {iris_response}")
                        self.stats['total_outputs'] += 1
                        self.stats['last_output'] = iris_response
                        
                        # Добавить в выходную очередь
                        self.output_queue.put(iris_response)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле обработки: {e}")
    
    def _output_loop(self):
        """Цикл синтеза речи"""
        while self.is_running:
            try:
                # Получить ответ
                try:
                    response = self.output_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Синтезировать речь
                if response and self.enable_voice_output:
                    # Прерывание если пользователь начал говорить
                    self.synthesizer.speak(
                        response,
                        interrupting=self.interruption_enabled
                    )
                    
                    self.last_speech_time = time.time()
                
            except Exception as e:
                logger.error(f"Ошибка в цикле выхода: {e}")
    
    def send_text(self, text: str, force: bool = False):
        """Отправить текст для обработки"""
        if not self.is_running and not force:
            logger.warning("Engine не запущен")
            return
        
        self._on_user_text(text)
    
    def respond(self, text: str, interrupting: bool = True):
        """Ответить голосом"""
        if self.enable_voice_output:
            self.synthesizer.speak(text, interrupting=interrupting)
        else:
            logger.info(f"[NO AUDIO] IRIS: {text}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        uptime = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'uptime': uptime,
            'is_running': self.is_running,
            'inputs_per_minute': self.stats['total_inputs'] / (uptime / 60) if uptime > 0 else 0,
            'outputs_per_minute': self.stats['total_outputs'] / (uptime / 60) if uptime > 0 else 0,
            'is_iris_speaking': self.synthesizer.is_speaking
        }


# ===================== ПРИМЕР ИСПОЛЬЗОВАНИЯ =====================
if __name__ == "__main__":
    print("=== IRIS VOICE ENGINE TEST ===")
    
    # Простой LLM callback для тестирования
    def simple_llm(text: str) -> str:
        responses = {
            'привет': 'Привет! Как дела?',
            'как дела': 'Отлично! Спасибо за вопрос!',
            'ирис': 'Я здесь! Слушаю тебя.',
            'помощь': 'Я помогу! О чём тебе рассказать?'
        }
        
        text_lower = text.lower()
        for key, value in responses.items():
            if key in text_lower:
                return value
        
        return f"Ты сказал: {text}. Интересно!"
    
    # Инициализация
    engine = IrisVoiceEngine(
        llm_callback=simple_llm,
        enable_voice_input=True,
        enable_voice_output=True
    )
    
    # Запуск
    engine.start()
    
    print("\n🎤 Voice Engine запущен!")
    print("Слушаю...\n")
    
    try:
        # Тестирование
        time.sleep(1)
        engine.send_text("Привет, Ирис!")
        
        time.sleep(3)
        engine.send_text("Как дела?")
        
        time.sleep(3)
        
        # Статистика
        stats = engine.get_stats()
        print(f"\nСтатистика:")
        print(f"  Входов: {stats['total_inputs']}")
        print(f"  Выходов: {stats['total_outputs']}")
        print(f"  Время: {stats['uptime']:.1f}с")
        
        # Ждём
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n\nОстановка...")
    finally:
        engine.stop()
        print("\n✅ Тест завершён")
