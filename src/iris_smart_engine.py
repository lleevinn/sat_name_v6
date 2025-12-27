"""
🚀 IRIS Smart Context & Priority Engine v2.1
Интеллектуальная система анализа и приоритизации событий
"""

import time
import threading
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass, field

class PlayerState(Enum):
    """Состояния игрока"""
    PLAYING = 1        # Активная игра
    SPECTATING = 2     # Наблюдение (мёртв)
    FREEZETIME = 3     # Подготовка раунда
    UNKNOWN = 4        # Неизвестное состояние

class EventPriority(Enum):
    """Приоритеты событий"""
    CRITICAL = 100     # Здоровье, смерть
    HIGH = 75          # Килы 3+, бомба
    MEDIUM = 50        # Обычные события
    LOW = 25           # Комментарии
    IGNORE = 0         # Игнорировать

class SmartContextAnalyzer:
    """Анализирует контекст события"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 2.0  # 2 секунды
    
    def analyze_ammo_situation(self, player, event_data: dict) -> Dict:
        """Анализирует ситуацию с боеприпасами"""
        mag = event_data.get('ammo_magazine', 0)
        reserve = event_data.get('ammo_reserve', 0)
        total = mag + reserve
        weapon = event_data.get('weapon', 'unknown')
        
        return {
            'magazine': mag,
            'reserve': reserve,
            'total': total,
            'weapon': weapon,
            'status': 'critical' if total <= 3 else 'low' if total <= 10 else 'medium',
            'advice_urgent': total <= 3,
        }
    
    def analyze_health_situation(self, player, event_data: dict) -> Dict:
        """Анализирует ситуацию с здоровьем"""
        hp = event_data.get('current_health', player.health)
        armor = player.armor if player else 0
        damage = event_data.get('damage', 0)
        
        status = 'critical' if hp <= 1 else 'very_low' if hp <= 15 else 'low' if hp <= 30 else 'medium'
        
        return {
            'health': hp,
            'armor': armor,
            'damage_taken': damage,
            'status': status,
            'is_critical': hp <= 15,
            'has_armor': armor > 0,
        }
    
    def analyze_kill_context(self, event_data: dict, player) -> Dict:
        """Анализирует контекст килла"""
        kills_this = event_data.get('round_kills', 0)
        streak = event_data.get('kill_streak', 0)
        headshot = event_data.get('headshot', False)
        weapon = event_data.get('weapon', 'unknown')
        
        # Определяем тип килла
        if kills_this >= 5:
            kill_type = 'ace'
        elif kills_this >= 4:
            kill_type = 'quadra'
        elif kills_this >= 3:
            kill_type = 'triple'
        elif kills_this >= 2:
            kill_type = 'double'
        else:
            kill_type = 'single'
        
        return {
            'round_kills': kills_this,
            'kill_streak': streak,
            'headshot': headshot,
            'weapon': weapon,
            'kill_type': kill_type,
            'is_special': kill_type in ['triple', 'quadra', 'ace'],
        }

class EventPriorityManager:
    """Управляет приоритетами событий"""
    
    def __init__(self):
        self.event_weights = {
            'low_health': (EventPriority.CRITICAL, "Здоровье критичное"),
            'low_ammo_warning': (EventPriority.HIGH, "Патроны кончаются"),
            'death': (EventPriority.CRITICAL, "Смерть"),
            'ace': (EventPriority.HIGH, "АЦЭ!"),
            'quadra_kill': (EventPriority.HIGH, "Четверка"),
            'triple_kill': (EventPriority.HIGH, "Тройка"),
            'double_kill': (EventPriority.MEDIUM, "Двойка"),
            'kill': (EventPriority.LOW, "Килл"),
            'heavy_damage': (EventPriority.MEDIUM, "Урон"),
            'bomb_planted': (EventPriority.HIGH, "Бомба!"),
            'bomb_defused': (EventPriority.HIGH, "Разминирована"),
            'round_start': (EventPriority.LOW, "Раунд начался"),
            'round_end': (EventPriority.MEDIUM, "Раунд закончился"),
        }
    
    def get_priority(self, event_type: str, event_data: dict = None) -> EventPriority:
        """Получить приоритет события"""
        priority, _ = self.event_weights.get(event_type, (EventPriority.LOW, ""))
        
        # Динамическое повышение приоритета
        if event_type == 'low_health' and event_data:
            hp = event_data.get('current_health', 50)
            if hp <= 1:
                priority = EventPriority.CRITICAL  # Макс приоритет
        
        return priority
    
    def should_interrupt(self, current_priority: EventPriority, new_priority: EventPriority) -> bool:
        """Должен ли новый event прервать текущий?"""
        # Прерываем если разница в приоритете >= 50
        return (new_priority.value - current_priority.value) >= 50

class PlayerStateTracker:
    """Отслеживает состояние игрока"""
    
    def __init__(self):
        self.current_state = PlayerState.UNKNOWN
        self.last_hp = 100
        self.last_state_change = time.time()
    
    def update(self, player_alive: bool, is_spectating: bool, round_phase: str = ""):
        """Обновляет состояние игрока"""
        old_state = self.current_state
        
        if not player_alive:
            self.current_state = PlayerState.SPECTATING
        elif round_phase == 'freezetime':
            self.current_state = PlayerState.FREEZETIME
        elif is_spectating:
            self.current_state = PlayerState.SPECTATING
        else:
            self.current_state = PlayerState.PLAYING
        
        if old_state != self.current_state:
            self.last_state_change = time.time()
    
    def is_in_game(self) -> bool:
        """Активно ли в игре?"""
        return self.current_state == PlayerState.PLAYING
    
    def is_spectating(self) -> bool:
        """В режиме наблюдения?"""
        return self.current_state == PlayerState.SPECTATING

class EventInterruptHandler:
    """Управляет прерыванием текущих событий"""
    
    def __init__(self):
        self.current_event = None
        self.current_priority = EventPriority.LOW
        self.speaking_lock = threading.Lock()
    
    def can_interrupt(self, new_priority: EventPriority) -> bool:
        """Может ли новое событие прервать текущее?"""
        return (new_priority.value - self.current_priority.value) >= 50
    
    def set_current_event(self, event_type: str, priority: EventPriority):
        """Установить текущее событие"""
        with self.speaking_lock:
            self.current_event = event_type
            self.current_priority = priority
    
    def clear_current_event(self):
        """Очистить текущее событие"""
        with self.speaking_lock:
            self.current_event = None
            self.current_priority = EventPriority.LOW

# ════════════════════════════════════════════════════════════

