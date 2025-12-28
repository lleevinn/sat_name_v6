"""
CONTEXT BUILDER v2.0 - РАСШИРЕННЫЙ АНАЛИЗ СИТУАЦИЙ
Анализирует все аспекты игровой ситуации для умного поведения IRIS
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from collections import deque


class SituationType(Enum):
    """Типы ситуаций в игре"""
    NORMAL = "normal"
    CLUTCH = "clutch"  # 1v5, 1v4 и т.д.
    LOW_HEALTH_CRITICAL = "low_health_critical"  # <= 15 HP
    LOW_HEALTH_WARNING = "low_health_warning"  # <= 30 HP
    LOW_AMMO_CRITICAL = "low_ammo_critical"  # <= 3 патрона
    LOW_AMMO_WARNING = "low_ammo_warning"  # <= 10 патронов
    LOW_MONEY_ECONOMY = "low_money_economy"  # < 2400, нужна эконом тактика
    FULL_BUY = "full_buy"  # Можем закупиться полностью
    ECO_ROUND = "eco_round"  # Экономный раунд, все экипируют минимум
    FORCE_BUY = "force_buy"  # Средний раунд, пытаемся закупиться
    MEGA_KILL_STREAK = "mega_kill_streak"  # >= 10 килл стрик
    HIGH_KILL_STREAK = "high_kill_streak"  # >= 3 килл стрик
    MULTI_KILL_ROUND = "multi_kill_round"  # >= 3 килла в этом раунде
    ACE = "ace"  # 5 килл в раунде
    LOSING_ROUND = "losing_round"  # Проигрываем раунд, враг на сайте
    WINNING_ROUND = "winning_round"  # Выигрываем раунд, враг на спаунах
    BOMB_PLANTED = "bomb_planted"  # Бомба заложена
    BOMB_DEFUSING = "bomb_defusing"  # Идёт разминирование
    TEAM_CLUTCH = "team_clutch"  # Команда против 3+ врагов


class EconomyStatus(Enum):
    """Статус экономики команды"""
    FULL_BUY = "full_buy"  # >= 14000 в команде
    HALF_BUY = "half_buy"  # 8000-14000
    FORCE_BUY = "force_buy"  # 4000-8000
    ECO = "eco"  # < 4000


@dataclass
class GameContext:
    """Контекст игровой ситуации"""
    # Персональные статы
    health: int
    armor: int
    weapon: str
    ammo_current: int
    ammo_reserve: int
    ammo_total: int
    money: int
    kill_streak: int
    round_kills: int
    round_headshots: int
    deaths_this_round: int
    
    # Ситуации в раунде
    situations: List[SituationType]
    
    # История событий (последние 5 событий)
    recent_events: List[Dict]
    
    # Статус команды
    team_alive: int
    enemy_alive: int
    economy_status: EconomyStatus
    
    # Статус раунда
    has_bomb: bool
    bomb_planted: bool
    is_bomb_site_enemy: bool
    is_bomb_site_friendly: bool
    
    # Временные метки
    round_number: int
    timestamp: datetime


class SmartContextBuilder:
    """Умный строитель контекста с полным анализом"""
    
    def __init__(self):
        self.recent_events: deque = deque(maxlen=10)  # История последних 10 событий
        self.round_start_time = None
        self.last_kill_streak = 0
        
    def build(self, player, cs2_gsi, event_type: str, event_data: Dict) -> GameContext:
        """
        Собрать полный контекст игровой ситуации
        
        Args:
            player: Текущий игрок
            cs2_gsi: Данные от CS2 GSI
            event_type: Тип события (kill, damage, ammo_low и т.д.)
            event_data: Данные события
            
        Returns:
            GameContext с полным анализом
        """
        
        # Извлечь базовые данные
        health = getattr(player, 'health', 100)
        armor = getattr(player, 'armor', 0)
        weapon = getattr(player, 'active_weapon', 'unknown')
        money = getattr(player, 'money', 0)
        kill_streak = getattr(player, 'kill_streak', 0)
        round_kills = getattr(player, 'round_kills', 0)
        round_headshots = getattr(player, 'round_headshots', 0)
        deaths_this_round = getattr(player, 'deaths_in_round', 0)
        
        # Патроны
        ammo_current = getattr(player, 'ammo_current', 0)
        ammo_reserve = getattr(player, 'ammo_reserve', 0)
        ammo_total = ammo_current + ammo_reserve
        
        # Ботинки
        has_bomb = event_data.get('has_bomb', False)
        bomb_planted = event_data.get('bomb_planted', False)
        
        # Враги и союзники
        team_alive = getattr(cs2_gsi, 'players_alive_ct', 5) if cs2_gsi else 5
        enemy_alive = getattr(cs2_gsi, 'players_alive_t', 5) if cs2_gsi else 5
        
        # Анализ типов ситуаций
        situations = self._analyze_situations(
            health, ammo_total, money, kill_streak, round_kills,
            team_alive, enemy_alive, weapon, bomb_planted
        )
        
        # Экономический статус
        economy_status = self._analyze_economy(money)
        
        # Сохранить событие в историю
        self.recent_events.append({
            'type': event_type,
            'timestamp': datetime.now(),
            'weapon': weapon,
            'data': event_data,
            'health': health,
            'money': money
        })
        
        # Определить, находится ли враг на сайте
        is_bomb_site_enemy = event_data.get('is_bomb_site_enemy', False)
        is_bomb_site_friendly = event_data.get('is_bomb_site_friendly', False)
        
        # Собрать контекст
        context = GameContext(
            health=health,
            armor=armor,
            weapon=weapon,
            ammo_current=ammo_current,
            ammo_reserve=ammo_reserve,
            ammo_total=ammo_total,
            money=money,
            kill_streak=kill_streak,
            round_kills=round_kills,
            round_headshots=round_headshots,
            deaths_this_round=deaths_this_round,
            situations=situations,
            recent_events=list(self.recent_events),
            team_alive=team_alive,
            enemy_alive=enemy_alive,
            economy_status=economy_status,
            has_bomb=has_bomb,
            bomb_planted=bomb_planted,
            is_bomb_site_enemy=is_bomb_site_enemy,
            is_bomb_site_friendly=is_bomb_site_friendly,
            round_number=event_data.get('round_number', 0),
            timestamp=datetime.now()
        )
        
        return context
    
    def _analyze_situations(self, health: int, ammo: int, money: int, 
                           kill_streak: int, round_kills: int,
                           team_alive: int, enemy_alive: int,
                           weapon: str, bomb_planted: bool) -> List[SituationType]:
        """Анализ всех активных ситуаций"""
        situations = []
        
        # === ЗДОРОВЬЕ ===
        if health <= 15:
            situations.append(SituationType.LOW_HEALTH_CRITICAL)
        elif health <= 30:
            situations.append(SituationType.LOW_HEALTH_WARNING)
        
        # === ПАТРОНЫ ===
        if ammo <= 3:
            situations.append(SituationType.LOW_AMMO_CRITICAL)
        elif ammo <= 10:
            situations.append(SituationType.LOW_AMMO_WARNING)
        
        # === ЭКОНОМИЯ ===
        if money < 2400:
            situations.append(SituationType.LOW_MONEY_ECONOMY)
        elif money >= 8000:
            situations.append(SituationType.FULL_BUY)
        
        # === КИЛЛ СТРИКИ ===
        if kill_streak >= 10:
            situations.append(SituationType.MEGA_KILL_STREAK)
        elif kill_streak >= 3:
            situations.append(SituationType.HIGH_KILL_STREAK)
        
        # === КИЛЛ В РАУНДЕ ===
        if round_kills >= 5:
            situations.append(SituationType.ACE)
        elif round_kills >= 3:
            situations.append(SituationType.MULTI_KILL_ROUND)
        
        # === CLUTCH СИТУАЦИЯ ===
        if self._is_clutch(team_alive, enemy_alive):
            situations.append(SituationType.CLUTCH)
        
        # === СОСТОЯНИЕ РАУНДА ===
        if team_alive <= 2 and enemy_alive >= 3:
            situations.append(SituationType.LOSING_ROUND)
        elif team_alive >= 3 and enemy_alive <= 2:
            situations.append(SituationType.WINNING_ROUND)
        
        # === БОМБА ===
        if bomb_planted:
            situations.append(SituationType.BOMB_PLANTED)
        
        if not situations:
            situations.append(SituationType.NORMAL)
        
        return situations
    
    def _is_clutch(self, team_alive: int, enemy_alive: int) -> bool:
        """Определить clutch ситуацию"""
        if team_alive <= 2 and enemy_alive >= 3:
            return True
        if team_alive == 1 and enemy_alive >= 2:
            return True
        return False
    
    def _analyze_economy(self, money: int) -> EconomyStatus:
        """Анализ личной экономики"""
        if money >= 8000:
            return EconomyStatus.FULL_BUY
        elif money >= 4000:
            return EconomyStatus.HALF_BUY
        elif money >= 2000:
            return EconomyStatus.FORCE_BUY
        else:
            return EconomyStatus.ECO
    
    def get_situation_priority(self, situations: List[SituationType]) -> int:
        """Определить приоритет ситуации"""
        priority_map = {
            SituationType.LOW_HEALTH_CRITICAL: 100,
            SituationType.LOW_AMMO_CRITICAL: 95,
            SituationType.ACE: 90,
            SituationType.CLUTCH: 85,
            SituationType.BOMB_PLANTED: 80,
            SituationType.LOSING_ROUND: 70,
            SituationType.WINNING_ROUND: 60,
            SituationType.MEGA_KILL_STREAK: 75,
            SituationType.MULTI_KILL_ROUND: 65,
            SituationType.LOW_HEALTH_WARNING: 50,
            SituationType.LOW_AMMO_WARNING: 45,
            SituationType.LOW_MONEY_ECONOMY: 40,
            SituationType.HIGH_KILL_STREAK: 55,
            SituationType.NORMAL: 10,
        }
        
        return max([priority_map.get(s, 0) for s in situations])
    
    def should_speak_now(self, situations: List[SituationType], 
                        recent_spoken: bool = False) -> bool:
        """Определить, должна ли IRIS говорить сейчас"""
        critical = [SituationType.LOW_HEALTH_CRITICAL, 
                   SituationType.LOW_AMMO_CRITICAL,
                   SituationType.BOMB_PLANTED]
        if any(s in situations for s in critical):
            return True
        
        if recent_spoken:
            return False
        
        import random
        return random.random() < 0.7
