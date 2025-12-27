#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_event_processor.py - ASYNC Интеграция CS2 GSI с IRIS Server

✨ ОПТИМИЗИРОВАННАЯ ВЕРСИЯ С:
- Асинхронной обработкой событий (параллельная обработка)
- Приоритетной очередью (критические события первыми)
- Кэшированием промптов (для fast respawn)
- Многопоточностью для максимальной скорости

Отвечает за:
1. Прослушивание событий от CS2 GSI
2. Обработка их в приоритетном порядке
3. Параллельная отправка в IRIS Server
4. Получение комментариев и выдача их игроку
5. Логирование всего происходящего

Архитектура:
    CS2 → GSI (порт 3000) → EventProcessor (async) → IRIS Server (порт 5000)

Использование:
    python iris_event_processor.py test
    python iris_event_processor.py
"""

import logging
import sys
import os
import json
import requests
import time
import threading
from pathlib import Path
from queue import PriorityQueue, Queue
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import hashlib

# FIX: Windows кодировка
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('iris_event_processor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# КОНФИГ
# ════════════════════════════════════════════════════════════════

IRIS_SERVER_URL = "http://localhost:5000"
GSI_PORT = 3000
PROCESSOR_PORT = 3001

# Приоритеты событий (меньше = выше приоритет)
EVENT_PRIORITIES = {
    'low_health': 1,        # КРИТИЧЕСКОЕ - первым!
    'low_ammo': 2,          # КРИТИЧЕСКОЕ
    'death': 3,             # Важное
    'double_kill': 4,       # Важное
    'triple_kill': 4,
    'quad_kill': 4,
    'kill': 5,              # Обычное
    'round_start': 10,      # Низкий приоритет
    'round_end': 10,
}

# Кэш промптов (чтобы не генерировать одно и то же)
PROMPT_CACHE = {}

# ════════════════════════════════════════════════════════════════
# МАППИРОВАНИЕ СОБЫТИЙ
# ════════════════════════════════════════════════════════════════

EVENT_MAPPING = {
    'kill': 'kill',
    'double_kill': 'multi_kill',
    'triple_kill': 'multi_kill',
    'quad_kill': 'multi_kill',
    'death': 'death',
    'low_health': 'low_health',
    'low_ammo_warning': 'low_ammo',
    'round_start': 'round_start',
    'round_end': 'round_end',
}

# ════════════════════════════════════════════════════════════════
# ASYNC EVENT PROCESSOR
# ════════════════════════════════════════════════════════════════

class AsyncEventProcessor:
    """Асинхронный процессор событий с приоритизацией и кэшем."""
    
    def __init__(self, iris_url: str = IRIS_SERVER_URL, max_workers: int = 4):
        self.iris_url = iris_url
        
        # Приоритетная очередь событий (priority, timestamp, event_type, data)
        self.event_queue = PriorityQueue()
        
        # Пул потоков для параллельной обработки
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Флаг обработки
        self.processing = False
        
        # Статистика
        self.stats = {
            'total_events': 0,
            'queued_events': 0,
            'successful': 0,
            'failed': 0,
            'cached_hits': 0,
            'response_times': []
        }
        
        # Кэш промптов
        self.prompt_cache = {}
        
        logger.info("\n" + "="*70)
        logger.info("🚀 ASYNC EVENT PROCESSOR ИНИЦИАЛИЗИРОВАН")
        logger.info(f"   Workers: {max_workers}")
        logger.info(f"   Mode: Priority Queue + Prompt Cache")
        logger.info("="*70)
    
    def is_iris_ready(self) -> bool:
        """Проверить что IRIS Server доступен."""
        try:
            response = requests.get(f"{self.iris_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _get_event_priority(self, event_type: str) -> int:
        """Получить приоритет события."""
        return EVENT_PRIORITIES.get(event_type, 10)
    
    def _get_prompt_cache_key(self, prompt: str) -> str:
        """Получить ключ кэша для промпта."""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def queue_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Добавить событие в приоритетную очередь.
        События с низким HP будут обработаны первыми!
        """
        priority = self._get_event_priority(event_type)
        timestamp = time.time()
        
        # Добавляем в очередь: (приоритет, временная метка, тип, данные)
        self.event_queue.put((priority, timestamp, event_type, event_data))
        self.stats['queued_events'] += 1
        
        logger.info(f"\n[QUEUE] 📥 Событие добавлено: {event_type} (приоритет: {priority})")
        logger.info(f"[QUEUE] 📊 В очереди: {self.event_queue.qsize()} событий")
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Основной метод обработки события.
        Запускается в отдельном потоке из пула!
        
        Args:
            event_type: Тип события (kill, death, etc.)
            event_data: Данные события
        
        Returns:
            Комментарий от IRIS или None если ошибка
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"[EVENT] 🎮 Получено событие: {event_type}")
        logger.info(f"[DATA]  {event_data}")
        logger.info(f"{'='*60}")
        
        self.stats['total_events'] += 1
        
        # Проверяем что IRIS доступна
        if not self.is_iris_ready():
            logger.error("[ERROR] ❌ IRIS Server недоступна! Пропускаем событие.")
            self.stats['failed'] += 1
            return None
        
        # Специальная обработка для каждого типа события
        if event_type == 'kill':
            return self._handle_kill(event_data)
        elif event_type == 'double_kill':
            return self._handle_multi_kill(event_data, 'double')
        elif event_type == 'triple_kill':
            return self._handle_multi_kill(event_data, 'triple')
        elif event_type == 'quad_kill':
            return self._handle_multi_kill(event_data, 'quad')
        elif event_type == 'death':
            return self._handle_death(event_data)
        elif event_type == 'low_health':
            return self._handle_low_health(event_data)
        elif event_type == 'low_ammo_warning':
            return self._handle_low_ammo(event_data)
        else:
            logger.warning(f"[WARN] ⚠️  Неизвестный тип события: {event_type}")
            return None
    
    def _handle_kill(self, data: Dict) -> Optional[str]:
        """Обработать убийство."""
        kills = data.get('round_kills', 1)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        headshot = data.get('headshot', False)
        
        logger.info(f"[KILL] 🎯 {kills}K убийство с {weapon}{' (HEADSHOT!)' if headshot else ''}")
        
        prompt = f"""
        Ты IRIS - веселый голосовой помощник для геймера CS2.
        
        Событие: Игрок совершил убийство!
        Детали:
        - Убийств в раунде: {kills}
        - Оружие: {weapon}
        - Headshot: {'ДА!' if headshot else 'Нет'}
        
        Дай КОРОТКИЙ (1-2 предложения) веселый комментарий на русском.
        Комментарий должен быть такой, чтобы его было прикольно слышать во время игры.
        """
        
        return self._send_to_iris_cached('kill', {'weapon': weapon, 'headshot': headshot, 'kills': kills}, prompt)
    
    def _handle_multi_kill(self, data: Dict, kill_type: str) -> Optional[str]:
        """Обработать множественное убийство."""
        kills = data.get('round_kills', 1)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        
        kill_name = {'double': 'ДВОЙНОЕ', 'triple': 'ТРОЙНОЕ', 'quad': 'ЧЕТВЕРНОЕ'}[kill_type]
        
        logger.info(f"[{kill_type.upper()}] 🔥 {kill_name} УБИЙСТВО с {weapon}!")
        
        prompt = f"""
        Ты IRIS - веселый голосовой помощник для геймера CS2.
        
        ВАЖНОЕ СОБЫТИЕ: {kill_name} УБИЙСТВО!
        Детали:
        - Тип: {kill_type} kill
        - Оружие: {weapon}
        - Убийств в раунде: {kills}
        
        Дай ОЧЕНЬ КОРОТКИЙ (1-2 короче предложения) восторженный комментарий на русском!
        Будь ЭКСПРЕССИВНЕЕ, это же {kill_name} УБИЙСТВО!
        """
        
        return self._send_to_iris_cached('multi_kill', {'type': kill_type, 'weapon': weapon, 'kills': kills}, prompt)
    
    def _handle_death(self, data: Dict) -> Optional[str]:
        """Обработать смерть."""
        total_deaths = data.get('total_deaths', 1)
        kd_ratio = data.get('kd_ratio', 0)
        
        logger.info(f"[DEATH] ☠️  Ты умер. KD Ratio: {kd_ratio}")
        
        prompt = f"""
        Ты IRIS - поддерживающий голосовой помощник для геймера CS2.
        
        Событие: Игрок погиб!
        Статистика:
        - Всего смертей: {total_deaths}
        - KD Ratio: {kd_ratio:.2f}
        
        Дай КОРОТКИЙ (1-2 предложения) поддерживающий комментарий на русском.
        Будь добрым и мотивирующим!
        """
        
        return self._send_to_iris_cached('death', {'kd_ratio': kd_ratio}, prompt)
    
    def _handle_low_health(self, data: Dict) -> Optional[str]:
        """Обработать КРИТИЧЕСКОЕ событие - низкое здоровье!"""
        health = data.get('current_health', 0)
        armor = data.get('armor', 0)
        
        logger.warning(f"[LOW_HEALTH] 🚨 КРИТИЧЕСКОЕ! HP: {health} | Armor: {armor}")
        
        prompt = f"""
        Ты IRIS - срочный голосовой помощник для геймера CS2.
        
        🚨 КРИТИЧЕСКОЕ ВНИМАНИЕ: Игрок ранен!
        Состояние:
        - Здоровье: {health} HP
        - Броня: {armor}
        
        Дай МАКСИМАЛЬНО КОРОТКИЙ (1 короткое предложение!) срочный совет на русском.
        Будь МАКСИМАЛЬНО кратким и срочным! Это критическое событие!
        """
        
        return self._send_to_iris_cached('low_health', {'health': health, 'armor': armor}, prompt)
    
    def _handle_low_ammo(self, data: Dict) -> Optional[str]:
        """Обработать критическое событие - мало амуниции!"""
        ammo = data.get('ammo_magazine', 0)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        
        logger.warning(f"[LOW_AMMO] 🚨 КРИТИЧЕСКОЕ! {weapon}: {ammo} патронов!")
        
        # Мало боезапаса - критическое, но не всегда нужно озвучивать
        if ammo <= 5:
            prompt = f"""
            Ты IRIS - срочный голосовой помощник для геймера CS2.
            
            🚨 КРИТИЧЕСКОЕ ВНИМАНИЕ: Мало амуниции!
            Детали:
            - Оружие: {weapon}
            - Патронов в магазине: {ammo}
            
            Дай МАКСИМАЛЬНО КОРОТКИЙ (1 слово или очень короткое предложение!) совет.
            """
            return self._send_to_iris_cached('low_ammo', {'ammo': ammo, 'weapon': weapon}, prompt)
        
        return None
    
    def _send_to_iris_cached(self, event_type: str, data: Dict, prompt: str) -> Optional[str]:
        """
        Отправить в IRIS с кэшированием промптов.
        Если похожий промпт уже был - используем кэш!
        """
        cache_key = self._get_prompt_cache_key(prompt)
        
        # Проверяем кэш
        if cache_key in self.prompt_cache:
            logger.info(f"[CACHE] ⚡ Попадание в кэш! Используем готовый ответ")
            self.stats['cached_hits'] += 1
            iris_response = self.prompt_cache[cache_key]
            logger.info(f"[IRIS_RESPONSE] {iris_response}")
            logger.info(f"[SPEED] ⚡ Ответ из кэша (мгновенный)")
            self.stats['successful'] += 1
            return iris_response
        
        # Иначе отправляем в IRIS
        return self._send_to_iris(event_type, data, prompt, cache_key)
    
    def _send_to_iris(self, event_type: str, data: Dict, prompt: str, cache_key: str) -> Optional[str]:
        """Отправить событие на IRIS Server и получить ответ."""
        try:
            start_time = time.time()
            
            logger.info("[SEND] 📤 Отправляю в IRIS Server...")
            
            response = requests.post(
                f"{self.iris_url}/say",
                json={"text": prompt},
                timeout=15
            )
            
            elapsed = time.time() - start_time
            self.stats['response_times'].append(elapsed)
            
            if response.status_code == 200:
                result = response.json()
                iris_response = result.get('response', 'No response')
                
                # Кэшируем ответ
                self.prompt_cache[cache_key] = iris_response
                
                logger.info(f"[IRIS_RESPONSE] {iris_response}")
                logger.info(f"[TIME] ⏱️  Ответ за {elapsed:.2f}с")
                logger.info(f"[CACHE] 💾 Ответ закэширован для быстрого доступа")
                
                self.stats['successful'] += 1
                return iris_response
            else:
                logger.error(f"[ERROR] IRIS вернула статус {response.status_code}")
                self.stats['failed'] += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error("[ERROR] ⏱️  Timeout при отправке в IRIS (более 15 сек)")
            self.stats['failed'] += 1
            return None
        
        except ConnectionError:
            logger.error("[ERROR] 🔌 Невозможно подключиться к IRIS Server")
            self.stats['failed'] += 1
            return None
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при отправке: {type(e).__name__}: {e}")
            self.stats['failed'] += 1
            return None
    
    def process_queue_async(self) -> None:
        """
        Обработать очередь событий асинхронно.
        События обрабатываются в фоновом потоке с приоритизацией!
        """
        self.processing = True
        logger.info("\n[ASYNC] 🔄 Запускаю обработку очереди в фоне...")
        
        def worker():
            while self.processing:
                try:
                    if not self.event_queue.empty():
                        # Получаем событие с НАИВЫСШИМ приоритетом
                        priority, timestamp, event_type, event_data = self.event_queue.get(timeout=1)
                        
                        # Обрабатываем в отдельном потоке из пула
                        self.executor.submit(self.process_event, event_type, event_data)
                    else:
                        time.sleep(0.1)
                except:
                    pass
        
        # Запускаем worker в фоновом потоке
        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()
    
    def print_stats(self):
        """Вывести статистику обработки."""
        logger.info("\n" + "="*60)
        logger.info("[STATS] 📊 СТАТИСТИКА ОБРАБОТКИ:")
        logger.info(f"  Всего событий: {self.stats['total_events']}")
        logger.info(f"  ✅ Успешно: {self.stats['successful']}")
        logger.info(f"  ❌ Ошибок: {self.stats['failed']}")
        logger.info(f"  ⚡ Попадания в кэш: {self.stats['cached_hits']}")
        logger.info(f"  📥 В очереди сейчас: {self.event_queue.qsize()}")
        
        if self.stats['response_times']:
            avg_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            max_time = max(self.stats['response_times'])
            min_time = min(self.stats['response_times'])
            logger.info(f"  ⏱️  Среднее время ответа: {avg_time:.2f}с")
            logger.info(f"  ⏱️  Мин/Макс: {min_time:.2f}с / {max_time:.2f}с")
        
        logger.info("="*60)

# ════════════════════════════════════════════════════════════════
# ТЕСТИРОВАНИЕ
# ════════════════════════════════════════════════════════════════

def test_processor():
    """Тестовый запуск с примерами событий."""
    logger.info("\n" + "="*60)
    logger.info("🧪 ТЕСТИРОВАНИЕ ASYNC EVENT PROCESSOR")
    logger.info("="*60)
    
    processor = AsyncEventProcessor(max_workers=4)
    
    # Проверка доступности IRIS
    logger.info("\n[TEST] ⏳ Проверка IRIS Server...")
    if processor.is_iris_ready():
        logger.info("✅ IRIS Server доступна!")
    else:
        logger.error("❌ IRIS Server недоступна!")
        logger.error("   Убедись что iris_server.py запущена на http://localhost:5000")
        return
    
    # Запускаем асинхронную обработку
    processor.process_queue_async()
    
    # Тестовые события (в СЛУЧАЙНОМ порядке, чтобы проверить приоритизацию!)
    test_events = [
        ('kill', {'round_kills': 1, 'weapon': 'weapon_fiveseven', 'headshot': True}),
        ('double_kill', {'round_kills': 2, 'weapon': 'weapon_awp', 'headshot': False}),
        ('low_health', {'current_health': 15, 'armor': 25}),  # КРИТИЧЕСКОЕ!
        ('death', {'total_deaths': 1, 'kd_ratio': 1.5}),
        ('low_ammo_warning', {'ammo_magazine': 3, 'weapon': 'weapon_ak47'}),  # КРИТИЧЕСКОЕ!
    ]
    
    logger.info("\n[TEST] 📨 Добавляю события в ПРИОРИТЕТНУЮ очередь...")
    logger.info("        (Notice: critical events будут обработаны ПЕРВЫМИ!)")
    
    for event_type, event_data in test_events:
        processor.queue_event(event_type, event_data)
        time.sleep(0.5)  # Небольшая пауза между добавлениями
    
    # Ждём обработки
    logger.info("\n[TEST] ⏳ Жду обработки всех событий (макс 60 сек)...")
    timeout = time.time() + 60
    while time.time() < timeout:
        if processor.event_queue.empty() and processor.stats['total_events'] == len(test_events):
            break
        time.sleep(0.5)
    
    # Выводим статистику
    processor.print_stats()
    logger.info("\n✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")

# ════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ════════════════════════════════════════════════════════════════

def main():
    """Главный запуск."""
    logger.info("\n" + "="*70)
    logger.info("🚀 ASYNC IRIS EVENT PROCESSOR v2.0")
    logger.info("   📊 Приоритетная очередь + Кэш промптов + Многопоточность")
    logger.info("="*70)
    logger.info(f"📍 IRIS Server: {IRIS_SERVER_URL}")
    logger.info(f"🎮 CS2 GSI: localhost:{GSI_PORT}")
    logger.info("="*70)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_processor()
    else:
        logger.info("\n[INFO] 🧪 Для тестирования запусти: python iris_event_processor.py test")
        logger.info("[INFO] 📚 Или используй как импортируемый модуль:")
        logger.info("       from iris_event_processor import AsyncEventProcessor")
        logger.info("       processor = AsyncEventProcessor()")
        logger.info("       processor.process_queue_async()")
        logger.info("       processor.queue_event('kill', {...})")

if __name__ == "__main__":
    main()
