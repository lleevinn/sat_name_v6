#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_event_processor.py - Интеграция CS2 GSI с IRIS Server

Отвечает за:
1. Прослушивание событий от CS2 GSI
2. Преобразование их в понятный для IRIS формат
3. Отправку в IRIS Server на обработку
4. Получение комментариев от IRIS
5. Логирование всего происходящего

Архитектура:
    CS2 → GSI (порт 3000) → Этот процесс → IRIS Server (порт 5000)

Использование:
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
from queue import Queue
from typing import Dict, Optional, Any
from datetime import datetime

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
PROCESSOR_PORT = 3001  # Для слушания кастомных событий

# Маппирование типов событий CS2 → IRIS
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
# EVENT PROCESSOR
# ════════════════════════════════════════════════════════════════

class EventProcessor:
    """Обрабатывает события CS2 и отправляет в IRIS Server."""
    
    def __init__(self, iris_url: str = IRIS_SERVER_URL):
        self.iris_url = iris_url
        self.event_queue = Queue()
        self.processing = False
        self.stats = {
            'total_events': 0,
            'successful': 0,
            'failed': 0,
            'response_times': []
        }
    
    def is_iris_ready(self) -> bool:
        """Проверить что IRIS Server доступен."""
        try:
            response = requests.get(f"{self.iris_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Основной метод обработки события.
        
        Args:
            event_type: Тип события (kill, death, etc.)
            event_data: Данные события
        
        Returns:
            Комментарий от IRIS или None если ошибка
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"[EVENT] Получено событие: {event_type}")
        logger.info(f"[DATA]  {event_data}")
        logger.info(f"{'='*60}")
        
        self.stats['total_events'] += 1
        
        # Проверяем что IRIS доступна
        if not self.is_iris_ready():
            logger.error("[ERROR] IRIS Server недоступна! Пропускаем событие.")
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
            logger.warning(f"[WARN] Неизвестный тип события: {event_type}")
            return None
    
    def _handle_kill(self, data: Dict) -> Optional[str]:
        """Обработать убийство."""
        kills = data.get('round_kills', 1)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        headshot = data.get('headshot', False)
        
        logger.info(f"[KILL] {kills}K убийство с {weapon}{' (HEADSHOT!)' if headshot else ''}")
        
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
        
        return self._send_to_iris('kill', {'weapon': weapon, 'headshot': headshot, 'kills': kills}, prompt)
    
    def _handle_multi_kill(self, data: Dict, kill_type: str) -> Optional[str]:
        """Обработать множественное убийство (double, triple, quad)."""
        kills = data.get('round_kills', 1)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        
        kill_name = {'double': 'ДВОЙНОЕ', 'triple': 'ТРОЙНОЕ', 'quad': 'ЧЕТВЕРНОЕ'}[kill_type]
        
        logger.info(f"[{kill_type.upper()}] {kill_name} УБИЙСТВО с {weapon}!")
        
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
        
        return self._send_to_iris('multi_kill', {'type': kill_type, 'weapon': weapon, 'kills': kills}, prompt)
    
    def _handle_death(self, data: Dict) -> Optional[str]:
        """Обработать смерть."""
        total_deaths = data.get('total_deaths', 1)
        kd_ratio = data.get('kd_ratio', 0)
        
        logger.info(f"[DEATH] Ты умер. KD Ratio: {kd_ratio}")
        
        prompt = f"""
        Ты IRIS - поддерживающий голосовой помощник для геймера CS2.
        
        Событие: Игрок погиб!
        Статистика:
        - Всего смертей: {total_deaths}
        - KD Ratio: {kd_ratio:.2f}
        
        Дай КОРОТКИЙ (1-2 предложения) поддерживающий комментарий на русском.
        Будь добрым и мотивирующим!
        """
        
        return self._send_to_iris('death', {'kd_ratio': kd_ratio}, prompt)
    
    def _handle_low_health(self, data: Dict) -> Optional[str]:
        """Обработать низкое здоровье."""
        health = data.get('current_health', 0)
        armor = data.get('armor', 0)
        
        logger.warning(f"[LOW_HEALTH] HP: {health} | Armor: {armor}")
        
        prompt = f"""
        Ты IRIS - заботливый голосовой помощник для геймера CS2.
        
        ВНИМАНИЕ: Игрок ранен!
        Состояние:
        - Здоровье: {health} HP
        - Броня: {armor}
        
        Дай ОЧЕНЬ КОРОТКИЙ (1 предложение) срочный совет на русском.
        Будь кратким и срочным!
        """
        
        return self._send_to_iris('low_health', {'health': health, 'armor': armor}, prompt)
    
    def _handle_low_ammo(self, data: Dict) -> Optional[str]:
        """Обработать низкий боезапас."""
        ammo = data.get('ammo_magazine', 0)
        weapon = data.get('weapon', 'unknown').replace('weapon_', '').upper()
        
        logger.warning(f"[LOW_AMMO] {weapon}: {ammo} патронов!")
        
        # Низкий боезапас - часто событие, не нужно озвучивать
        logger.info("[SKIP] Событие низкого боезапаса не отправляем (слишком часто)")
        return None
    
    def _send_to_iris(self, event_type: str, data: Dict, prompt: str) -> Optional[str]:
        """Отправить событие на IRIS Server и получить ответ."""
        try:
            start_time = time.time()
            
            # Отправляем на /say endpoint (генерирует ответ)
            response = requests.post(
                f"{self.iris_url}/say",
                json={"text": prompt},
                timeout=10
            )
            
            elapsed = time.time() - start_time
            self.stats['response_times'].append(elapsed)
            
            if response.status_code == 200:
                result = response.json()
                iris_response = result.get('response', 'No response')
                
                logger.info(f"[IRIS_RESPONSE] {iris_response}")
                logger.info(f"[TIME] Ответ за {elapsed:.2f}с")
                
                self.stats['successful'] += 1
                return iris_response
            else:
                logger.error(f"[ERROR] IRIS вернула статус {response.status_code}")
                self.stats['failed'] += 1
                return None
        
        except requests.exceptions.Timeout:
            logger.error("[ERROR] Timeout при отправке в IRIS")
            self.stats['failed'] += 1
            return None
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при отправке: {e}")
            self.stats['failed'] += 1
            return None
    
    def print_stats(self):
        """Вывести статистику обработки."""
        logger.info("\n" + "="*60)
        logger.info("[STATS] Статистика обработки событий:")
        logger.info(f"  Всего событий: {self.stats['total_events']}")
        logger.info(f"  Успешно: {self.stats['successful']}")
        logger.info(f"  Ошибок: {self.stats['failed']}")
        
        if self.stats['response_times']:
            avg_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            logger.info(f"  Среднее время ответа: {avg_time:.2f}с")
        
        logger.info("="*60)

# ════════════════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ С TEST_CS2_GSI
# ════════════════════════════════════════════════════════════════

def integrate_with_gsi(processor: EventProcessor):
    """
    Этот код нужно добавить в test_cs2_gsi.py:
    
    # После создания GSI инстанса:
    event_processor = EventProcessor()
    
    # В функцию handle_game_event добавить:
    def handle_game_event(event: GameEvent):
        if not event_filter.is_player_event(event):
            return
        
        logger.info(f"[EVENT] {event.event_type}: {event.data}")
        
        # НОВАЯ СТРОКА:
        response = event_processor.process_event(event.event_type, event.data)
        if response:
            logger.info(f"[IRIS] {response}")
    """
    pass

# ════════════════════════════════════════════════════════════════
# ТЕСТИРОВАНИЕ
# ════════════════════════════════════════════════════════════════

def test_processor():
    """Тестовый запуск с примерами событий."""
    logger.info("\n" + "="*60)
    logger.info("🧪 ТЕСТИРОВАНИЕ IRIS EVENT PROCESSOR")
    logger.info("="*60)
    
    processor = EventProcessor()
    
    # Проверка доступности IRIS
    logger.info("\n[TEST] Проверка IRIS Server...")
    if processor.is_iris_ready():
        logger.info("✅ IRIS Server доступна!")
    else:
        logger.error("❌ IRIS Server недоступна!")
        logger.error("   Убедись что iris_server.py запущена на http://localhost:5000")
        return
    
    # Тестовые события
    test_events = [
        ('kill', {'round_kills': 1, 'weapon': 'weapon_fiveseven', 'headshot': True}),
        ('double_kill', {'round_kills': 2, 'weapon': 'weapon_awp', 'headshot': False}),
        ('low_health', {'current_health': 25, 'armor': 50}),
        ('death', {'total_deaths': 1, 'kd_ratio': 1.5}),
    ]
    
    logger.info("\n[TEST] Отправка тестовых событий...")
    for event_type, event_data in test_events:
        logger.info(f"\n>>> Тестирую {event_type}...")
        processor.process_event(event_type, event_data)
        time.sleep(1)  # Пауза между событиями
    
    # Статистика
    processor.print_stats()

# ════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ════════════════════════════════════════════════════════════════

def main():
    """Главный запуск."""
    logger.info("\n" + "="*70)
    logger.info("🔧 IRIS EVENT PROCESSOR - Интеграция CS2 GSI ↔ IRIS Server")
    logger.info("="*70)
    logger.info(f"📍 IRIS Server: {IRIS_SERVER_URL}")
    logger.info(f"🎮 CS2 GSI: localhost:{GSI_PORT}")
    logger.info("="*70)
    
    # Если запущено с аргументом "test" - запускаем тесты
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_processor()
    else:
        logger.info("\n[INFO] Для тестирования запусти: python iris_event_processor.py test")
        logger.info("[INFO] Или используй как импортируемый модуль:")
        logger.info("       from iris_event_processor import EventProcessor")

if __name__ == "__main__":
    main()
