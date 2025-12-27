# ════════════════════════════════════════════════════════════════════════════════════
# 🎯 TTS QUEUE MANAGER - Управление очередью с приоритетами и без спама
# ════════════════════════════════════════════════════════════════════════════════════

import threading
import time
import logging
from collections import deque
from typing import Optional, Dict

logger = logging.getLogger("IRIS")


class TTSQueueManager:
    """
    Менеджер очереди TTS с приоритетами и дебаунсером
    
    Решает проблемы:
    ✅ Спам озвучек - максимум 1 озвучка одновременно
    ✅ Долгие ожидания - приоритетная очередь (критичные события сразу)
    ✅ Перекрывающиеся события - дебаунсер 300мс между озвучками
    ✅ Переполнение памяти - максимум N элементов в очереди
    """
    
    PRIORITY_CRITICAL = 10  # Критичные события (низко ХП, нет патронов)
    PRIORITY_KILL = 8       # Килы и мультикилы
    PRIORITY_REGULAR = 5    # Обычные события
    PRIORITY_COMMENT = 1    # Случайные комментарии
    
    def __init__(self, tts_engine, max_queue_size: int = 8):
        """
        Инициализировать менеджер очереди
        
        Args:
            tts_engine: Объект TTSEngine для озвучивания
            max_queue_size: Максимальный размер очереди (8 по умолчанию)
        """
        self.tts = tts_engine
        self.queue: deque = deque(maxlen=max_queue_size)
        self.last_speak_time = 0.0
        self.debounce_interval = 0.3  # 300мс между озвучками
        self.is_speaking = False
        self.lock = threading.Lock()
        self.processor_thread: Optional[threading.Thread] = None
        self.is_running = False
        
    def add(self, text: str, emotion: str = 'neutral', priority: int = None) -> bool:
        """
        Добавить элемент в очередь
        
        Args:
            text: Текст для озвучивания
            emotion: Эмоция для TTS (neutral, excited, tense, happy, gentle и т.д.)
            priority: Приоритет (по умолчанию PRIORITY_REGULAR)
        
        Returns:
            True если успешно добавлен, False если очередь переполнена
        """
        if priority is None:
            priority = self.PRIORITY_REGULAR
        
        with self.lock:
            if len(self.queue) >= self.queue.maxlen:
                logger.warning(f"[TTS] Очередь переполнена ({len(self.queue)} элементов)")
                return False
            
            self.queue.append({
                'text': text.strip(),
                'emotion': emotion,
                'priority': priority,
                'timestamp': time.time()
            })
            logger.debug(f"[TTS] Добавлено: {text[:60]} (приоритет {priority})")
            return True
    
    def start(self):
        """Запустить обработчик очереди в отдельном потоке"""
        if self.is_running:
            return
        
        self.is_running = True
        self.processor_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="TTSQueueProcessor"
        )
        self.processor_thread.start()
        logger.info("[TTS] Queue Manager запущен")
    
    def stop(self):
        """Остановить обработчик очереди"""
        self.is_running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=2)
        logger.info("[TTS] Queue Manager остановлен")
    
    def _process_loop(self):
        """Основной цикл обработки очереди - работает в отдельном потоке"""
        while self.is_running:
            now = time.time()
            
            # ✅ Проверяем дебаунс (не спешим между озвучками)
            if now - self.last_speak_time < self.debounce_interval:
                time.sleep(0.05)
                continue
            
            # ✅ Проверяем, не говорит ли TTS
            if self.tts.is_busy():
                time.sleep(0.1)
                continue
            
            with self.lock:
                if not self.queue:
                    time.sleep(0.1)
                    continue
                
                # ✅ Выбираем элемент с наивысшим приоритетом
                item = max(self.queue, key=lambda x: (x['priority'], -x['timestamp']))
                self.queue.remove(item)
            
            # ✅ Озвучиваем
            try:
                self.tts.speak(item['text'], emotion=item['emotion'])
                self.last_speak_time = time.time()
                
                priority_name = {
                    10: "CRITICAL",
                    8: "KILL",
                    5: "REGULAR",
                    1: "COMMENT"
                }.get(item['priority'], f"P{item['priority']}")
                
                logger.info(f"[TTS] 🎤 [{priority_name}] {item['text'][:70]}")
            except Exception as e:
                logger.error(f"[TTS] ❌ Ошибка озвучки: {e}")
    
    def get_queue_size(self) -> int:
        """Получить текущий размер очереди"""
        with self.lock:
            return len(self.queue)
    
    def get_status(self) -> Dict:
        """Получить детальный статус менеджера"""
        return {
            'queue_size': self.get_queue_size(),
            'is_running': self.is_running,
            'last_speak_time': self.last_speak_time,
            'debounce_interval': self.debounce_interval,
        }
