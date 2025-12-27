"""
IRIS TTS Engine v3.1 - Эмоциональный голос с приоритизацией
Поддержка SSML для естественной эмоциональной речи
+ НОВОЕ: interrupt(), flush(), wait_until_silent()
"""

import asyncio
import threading
import queue
import time
import os
import tempfile
from typing import Optional, Callable, Dict, Any, Tuple
from enum import Enum

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("[TTS] Edge TTS не установлен. Установите: pip install edge-tts")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[TTS] Pygame не установлен. Установите: pip install pygame")

class EmotionType(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    GENTLE = "gentle"
    SUPPORTIVE = "supportive"
    TENSE = "tense"
    SAD = "sad"
    SARCASTIC = "sarcastic"
    PROUD = "proud"
    ENCOURAGING = "encouraging"

class TTSEngine:
    """
    Эмоциональный движок синтеза речи для Ирис
    Использует Edge TTS с SSML для естественной интонации
    """

    VOICE_PRESETS = {
        'ru_female_soft': 'ru-RU-SvetlanaNeural',
        'ru_female_energetic': 'ru-RU-DariyaNeural',
        'ru_male_deep': 'ru-RU-DmitryNeural',
        'en_female': 'en-US-JennyNeural',
        'en_male': 'en-US-GuyNeural',
    }

    EMOTION_SSML_PARAMS = {
        'neutral': {'rate': '+0%', 'pitch': '+0Hz', 'volume': '+0%'},
        'happy': {'rate': '+10%', 'pitch': '+15Hz', 'volume': '+5%'},
        'excited': {'rate': '+20%', 'pitch': '+25Hz', 'volume': '+10%'},
        'gentle': {'rate': '-10%', 'pitch': '-5Hz', 'volume': '-5%'},
        'supportive': {'rate': '+0%', 'pitch': '+8Hz', 'volume': '+0%'},
        'tense': {'rate': '+5%', 'pitch': '+5Hz', 'volume': '+5%'},
        'sad': {'rate': '-15%', 'pitch': '-10Hz', 'volume': '-10%'},
        'sarcastic': {'rate': '+5%', 'pitch': '-8Hz', 'volume': '+5%'},
        'proud': {'rate': '+8%', 'pitch': '+12Hz', 'volume': '+8%'},
        'encouraging': {'rate': '+5%', 'pitch': '+10Hz', 'volume': '+5%'},
    }

    EMOTION_PHRASES = {
        'happy': ['Ура!', 'Отлично!', 'Прекрасно!', 'Супер!'],
        'excited': ['Вау!', 'Невероятно!', 'Потрясающе!'],
        'supportive': ['Не волнуйся', 'Всё будет хорошо', 'Ты справишься'],
        'proud': ['Горжусь тобой!', 'Молодец!', 'Так держать!'],
    }

    def __init__(self,
                 voice: str = 'ru_female_soft',
                 rate: int = 0,
                 volume: float = 0.9,
                 visual_callback: Optional[Callable] = None,
                 max_queue_size: int = 10):
        """
        Инициализация эмоционального TTS движка
        Args:
            voice: Предустановка голоса
            rate: Базовая скорость речи
            volume: Громкость (0.0 до 1.0)
            visual_callback: Функция визуальной обратной связи
            max_queue_size: Максимальный размер очереди
        """
        print("[TTS] Инициализация эмоционального движка Ирис v3.1...")
        
        if not EDGE_TTS_AVAILABLE:
            raise RuntimeError("Edge TTS не установлен")
        if not PYGAME_AVAILABLE:
            raise RuntimeError("Pygame не установлен")
        
        self._init_pygame()

        self.voice_preset = voice
        self.base_rate = rate
        self.base_volume = volume
        self.visual_callback = visual_callback
        
        # ✅ НОВОЕ: Приоритетная очередь с max_queue_size
        self.message_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size
        
        self.is_running = False
        self.currently_speaking = False
        self.current_emotion = EmotionType.NEUTRAL
        self.processing_thread = None
        self._message_counter = 0
        self.temp_files = []
        
        # ✅ НОВОЕ: Флаг для прерывания текущей речи
        self._interrupt_flag = False
        
        # ✅ НОВОЕ: Event для синхронизации
        self._speaking_done = threading.Event()
        self._speaking_done.set()
        
        print(f"[TTS] Голос: {voice}, Громкость: {volume}")
        print(f"[TTS] Max queue size: {max_queue_size}")
        print("[TTS] Движок готов к работе")

    def _init_pygame(self):
        """Безопасная инициализация pygame mixer"""
        self.audio_available = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
            self.audio_available = True
            print("[TTS] Pygame mixer инициализирован")
        except Exception as e:
            print(f"[TTS] Аудио устройство недоступно: {e}")
            print("[TTS] Режим симуляции (текст будет выводиться в консоль)")
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=4096)
                self.audio_available = True
            except:
                self.audio_available = False

    def _get_voice_id(self) -> str:
        """Получение ID голоса Edge TTS"""
        if self.voice_preset in self.VOICE_PRESETS:
            return self.VOICE_PRESETS[self.voice_preset]
        return self.VOICE_PRESETS['ru_female_soft']

    def _build_ssml(self, text: str, emotion: str) -> str:
        """
        Построение SSML разметки для эмоциональной речи
        Args:
            text: Исходный текст
            emotion: Тип эмоции
        Returns:
            SSML строка с эмоциональной разметкой
        """
        voice_id = self._get_voice_id()
        params = self.EMOTION_SSML_PARAMS.get(emotion, self.EMOTION_SSML_PARAMS['neutral'])
        
        ssml = f'''<speak version="1.0" xml:lang="ru-RU">
<voice name="{voice_id}" rate="{params['rate']}" pitch="{params['pitch']}">
{self._add_pauses(text, emotion)}
</voice>
</speak>'''
        return ssml

    def _add_pauses(self, text: str, emotion: str) -> str:
        """Добавление естественных пауз в текст"""
        import re
        text = re.sub(r'([.!?])\s+', r'\1', text)
        text = re.sub(r'([,;:])\s+', r'\1', text)
        if emotion in ['happy', 'excited', 'proud']:
            text = re.sub(r'!', r'!', text)
        return text

    async def _synthesize_async(self, text: str, emotion: str = 'neutral') -> Optional[str]:
        """
        Асинхронный синтез речи с Edge TTS
        Returns:
            Путь к временному аудиофайлу или None
        """
        if not text or not isinstance(text, str):
            return None

        text = text.strip()
        if not text:
            return None

        try:
            voice_id = self._get_voice_id()
            params = self.EMOTION_SSML_PARAMS.get(emotion, self.EMOTION_SSML_PARAMS['neutral'])
            rate = params['rate']
            pitch = params['pitch']

            communicate = edge_tts.Communicate(
                text=text,
                voice=voice_id,
                rate=rate,
                pitch=pitch
            )

            tmp_file = tempfile.NamedTemporaryFile(
                suffix='.mp3',
                delete=False,
                prefix='iris_tts_'
            )

            tmp_path = tmp_file.name
            tmp_file.close()

            await communicate.save(tmp_path)
            self.temp_files.append(tmp_path)
            return tmp_path

        except Exception as e:
            print(f"[TTS] Ошибка синтеза: {e}")
            return None

    def _play_audio(self, audio_path: str) -> bool:
        """
        Воспроизведение аудиофайла через pygame
        Args:
            audio_path: Путь к аудиофайлу
        Returns:
            True если успешно
        """
        if not audio_path or not os.path.exists(audio_path):
            print("[TTS] Аудиофайл не найден")
            return False

        try:
            if self.visual_callback:
                self.visual_callback(True, 0.8)

            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.set_volume(self.base_volume)
            pygame.mixer.music.play()

            # ✅ НОВОЕ: Проверка флага прерывания во время воспроизведения
            while pygame.mixer.music.get_busy():
                if self._interrupt_flag:
                    pygame.mixer.music.stop()
                    print("[TTS] ⚠️ Воспроизведение прервано")
                    break
                
                pygame.time.Clock().tick(30)

                if self.visual_callback:
                    import random
                    intensity = 0.5 + random.random() * 0.3
                    self.visual_callback(True, intensity)

            pygame.mixer.music.stop()
            
            try:
                pygame.mixer.music.unload()
            except:
                pass

            if self.visual_callback:
                self.visual_callback(False, 0.0)

            return True

        except Exception as e:
            print(f"[TTS] Ошибка воспроизведения: {e}")
            if self.visual_callback:
                self.visual_callback(False, 0.0)
            return False

        finally:
            try:
                if audio_path in self.temp_files:
                    self.temp_files.remove(audio_path)
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
            except:
                pass

    def _process_queue(self):
        """Основной цикл обработки очереди"""
        print("[TTS] Запуск обработчика очереди...")
        
        while self.is_running:
            try:
                # ✅ НОВОЕ: Используем timeout для проверки флага
                try:
                    priority, counter, (text, emotion) = self.message_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # ✅ НОВОЕ: Проверка флага прерывания перед обработкой
                if self._interrupt_flag:
                    self.message_queue.task_done()
                    continue

                self.currently_speaking = True
                self._speaking_done.clear()

                self.current_emotion = EmotionType(emotion) if emotion in [e.value for e in EmotionType] else EmotionType.NEUTRAL

                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    audio_path = loop.run_until_complete(
                        self._synthesize_async(text, emotion)
                    )
                    loop.close()

                    if audio_path:
                        if self.audio_available:
                            success = self._play_audio(audio_path)
                            if success:
                                print(f"[TTS] ✅ Озвучено: '{text[:40]}...' [{emotion}]")
                            else:
                                print(f"[TTS] 💬 [{emotion.upper()}]: {text}")
                        else:
                            print(f"[TTS] 💬 [{emotion.upper()}]: {text}")

                        try:
                            if os.path.exists(audio_path):
                                os.unlink(audio_path)
                        except:
                            pass

                except Exception as e:
                    print(f"[TTS] Ошибка обработки: {e}")

                finally:
                    self.currently_speaking = False
                    self._speaking_done.set()  # ✅ НОВОЕ: Сигнал о завершении
                    self.message_queue.task_done()

            except Exception as e:
                print(f"[TTS] Ошибка в цикле: {e}")
                self.currently_speaking = False
                self._speaking_done.set()

    def speak(self, text: str, emotion: str = 'neutral', priority: bool = False):
        """
        Добавление сообщения в очередь на озвучивание
        Args:
            text: Текст для озвучивания
            emotion: Эмоциональная окраска
            priority: Приоритетное сообщение
        """
        if not text or not isinstance(text, str):
            return

        text = text.strip()
        if not text:
            return

        if emotion not in self.EMOTION_SSML_PARAMS:
            emotion = 'neutral'

        message_priority = 0 if priority else 1
        self._message_counter += 1
        counter = self._message_counter

        try:
            # ✅ НОВОЕ: Обработка переполнения очереди
            try:
                self.message_queue.put(
                    (message_priority, counter, (text, emotion)),
                    block=False
                )
            except queue.Full:
                print(f"[TTS] ⚠️ Очередь переполнена ({self.max_queue_size}), пропускаем сообщение")
                return

            if not self.is_running:
                print("[TTS] Внимание: движок не запущен, вызовите start()")

        except Exception as e:
            print(f"[TTS] Ошибка добавления: {e}")

    def speak_with_emotion(self, text: str, context: Dict[str, Any] = None):
        """
        Умное озвучивание с автоматическим определением эмоции
        Args:
            text: Текст для озвучивания
            context: Контекст (game_event, user_mood, etc.)
        """
        emotion = self._detect_emotion(text, context)
        self.speak(text, emotion)

    def _detect_emotion(self, text: str, context: Dict[str, Any] = None) -> str:
        """Автоматическое определение эмоции по тексту и контексту"""
        text_lower = text.lower()

        happy_words = ['круто', 'отлично', 'прекрасно', 'здорово', 'супер', 'класс', 'молодец', 'ура']
        excited_words = ['невероятно', 'потрясающе', 'вау', 'офигеть', 'эйс', 'ace', 'клатч']
        supportive_words = ['ничего', 'бывает', 'не переживай', 'справишься', 'в следующий раз']
        sad_words = ['жаль', 'обидно', 'к сожалению', 'увы']

        if any(word in text_lower for word in excited_words):
            return 'excited'
        if any(word in text_lower for word in happy_words):
            return 'happy'
        if any(word in text_lower for word in supportive_words):
            return 'supportive'
        if any(word in text_lower for word in sad_words):
            return 'gentle'

        if context:
            event_type = context.get('event_type', '')
            if event_type == 'kill':
                return 'excited' if context.get('headshot') else 'happy'
            elif event_type == 'death':
                return 'supportive'
            elif event_type == 'round_win':
                return 'proud'
            elif event_type == 'round_loss':
                return 'encouraging'
            elif event_type == 'ace':
                return 'excited'
            elif event_type == 'clutch':
                return 'excited'

        return 'neutral'

    def is_busy(self) -> bool:
        """Проверка занятости движка"""
        return self.currently_speaking or not self.message_queue.empty()

    # ✅ НОВЫЕ МЕТОДЫ ДЛЯ СИНХРОНИЗАЦИИ

    def interrupt(self):
        """
        Прерывание текущей речи (останавливает воспроизведение)
        ВАЖНО: Не очищает очередь, только текущее сообщение
        """
        if self.currently_speaking:
            self._interrupt_flag = True
            print("[TTS] 🛑 Прерывание текущей речи...")
            
            try:
                pygame.mixer.music.stop()
            except:
                pass
            
            # Ожидаем завершения
            timeout = time.time() + 1.0
            while self.currently_speaking and time.time() < timeout:
                time.sleep(0.05)
            
            self._interrupt_flag = False

    def flush(self):
        """
        Очистка очереди (удаляет все ожидающие сообщения)
        """
        self.interrupt()  # Сначала прерываем текущее
        
        cleared_count = 0
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
                self.message_queue.task_done()
                cleared_count += 1
            except queue.Empty:
                break
        
        if cleared_count > 0:
            print(f"[TTS] 🧹 Очищено {cleared_count} сообщений из очереди")

    def wait_until_silent(self, timeout: float = 10.0) -> bool:
        """
        Ждём, пока Ирис закончит говорить (все сообщения обработаны)
        Args:
            timeout: Максимальное время ожидания в секундах
        Returns:
            True если система молчит, False если timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_busy():
                print("[TTS] ✅ Система молчит")
                return True
            time.sleep(0.1)
        
        print(f"[TTS] ⚠️ Timeout: система не замолчала за {timeout}с")
        return False

    def clear_queue(self):
        """Очистка очереди (без прерывания текущего)"""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
                self.message_queue.task_done()
            except queue.Empty:
                break

    def start(self):
        """Запуск движка TTS"""
        if self.is_running:
            return

        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="IrisTTS-Processor"
        )
        self.processing_thread.start()
        print("[TTS] ✅ Эмоциональный движок Ирис запущен")

    def stop(self):
        """Остановка движка TTS"""
        if not self.is_running:
            return

        print("[TTS] Остановка движка...")
        
        self.flush()  # Очищаем и прерываем
        self.is_running = False

        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)

        try:
            pygame.mixer.music.stop()
        except:
            pass

        for tmp_file in self.temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except:
                pass

        self.temp_files.clear()
        print("[TTS] Движок остановлен")

    def change_voice(self, voice_name: str):
        """Смена голоса"""
        if voice_name in self.VOICE_PRESETS:
            self.voice_preset = voice_name
            print(f"[TTS] Голос: {voice_name}")
        else:
            print(f"[TTS] Голос не найден: {voice_name}")

    def change_volume(self, volume: float):
        """Изменение громкости"""
        if 0.0 <= volume <= 1.0:
            self.base_volume = volume

    def get_queue_size(self) -> int:
        """Получить текущий размер очереди"""
        return self.message_queue.qsize()

    def set_max_queue_size(self, size: int):
        """Изменить максимальный размер очереди (требует пересоздания)"""
        self.max_queue_size = size
        print(f"[TTS] Max queue size изменён на {size}")


if __name__ == "__main__":
    print("=== Тест эмоционального TTS Ирис v3.1 ===\n")

    try:
        tts = TTSEngine(voice='ru_female_soft', volume=0.8, max_queue_size=5)
        tts.start()

        print("1. Нейтральная речь:")
        tts.speak("Привет! Я Ирис, твой AI компаньон для стримов.", emotion='neutral')
        tts.wait_until_silent(timeout=10)

        print("\n2. Радостная речь:")
        tts.speak("Отлично сыграно! Ты просто молодец!", emotion='happy')
        tts.wait_until_silent(timeout=10)

        print("\n3. Возбуждённая речь:")
        tts.speak("Вау! Невероятный хедшот! Это было потрясающе!", emotion='excited')
        tts.wait_until_silent(timeout=10)

        print("\n4. Поддерживающая речь:")
        tts.speak("Ничего страшного, в следующий раз обязательно получится.", emotion='supportive')
        tts.wait_until_silent(timeout=10)

        print("\n5. Тест приоритета:")
        tts.speak("Долгое сообщение с низким приоритетом...", emotion='neutral')
        time.sleep(1)
        tts.speak("СРОЧНО! Критичная информация!", emotion='excited', priority=True)
        tts.wait_until_silent(timeout=15)

        print("\nТест завершен!")
        tts.stop()

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
