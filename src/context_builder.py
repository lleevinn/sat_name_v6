# ════════════════════════════════════════════════════════════════════════════════════
# 🧠 SMART CONTEXT BUILDER - Правильное построение контекста игрока
# ════════════════════════════════════════════════════════════════════════════════════

import logging
import traceback
from typing import Optional, Dict

logger = logging.getLogger("IRIS")


class SmartContextBuilder:
    """
    Построение полного контекста игрока с валидацией и fallback значениями
    
    Решает проблемы:
    ✅ None значения - всегда возвращает корректные числа
    ✅ Неполные данные - использует fallback значения
    ✅ Кривые значения - валидация диапазонов
    ✅ Безопасность - защита от некорректных типов данных
    """
    
    @staticmethod
    def build(player, cs2_gsi, event_type: str, event_data: Dict) -> Optional[Dict]:
        """
        Построить полный контекст игрока
        
        Args:
            player: Объект игрока из CS2GSI
            cs2_gsi: Объект CS2GameStateIntegration
            event_type: Тип события (kill, damage и т.д.)
            event_data: Словарь с данными события
        
        Returns:
            Словарь с полным контекстом игрока или None если ошибка
        """
        
        if not player:
            logger.warning("[CONTEXT] Игрок не найден")
            return None
        
        try:
            # ✅ Основные параметры с валидацией диапазонов
            hp = max(0, min(100, int(player.health or 100)))
            armor = max(0, int(player.armor or 0))
            money = max(0, int(player.money or 0))
            
            # ✅ Оружие с fallback
            weapon = str(player.weapon or "rifle")
            if 'IReadOnly' in weapon or len(weapon) < 2:
                weapon = "rifle"
            weapon = weapon.split('_')[-1][:15]  # Берём последнюю часть названия
            
            # ✅ Патроны с валидацией
            mag = max(0, int(player.ammo_in_magazine or 0))
            reserve = max(0, int(player.ammo_in_reserve or 0))
            total_ammo = mag + reserve
            
            # ✅ Kill streak и раунд килы
            kill_streak = max(0, int(cs2_gsi.kill_streak or 0)) if cs2_gsi else 0
            round_kills = max(0, int(event_data.get('round_kills', 0)))
            
            # ✅ Счет раунда
            map_info = cs2_gsi.map if cs2_gsi else None
            ct_score = max(0, int(map_info.ct_score or 0)) if map_info else 0
            t_score = max(0, int(map_info.t_score or 0)) if map_info else 0
            
            # ✅ Позиция и команда
            is_ct = player.team == 3 if hasattr(player, 'team') else False
            
            # ✅ Формируем полный контекст
            context = {
                'health': hp,
                'armor': armor,
                'money': money,
                'weapon': weapon,
                'ammo_mag': mag,
                'ammo_reserve': reserve,
                'ammo_total': total_ammo,
                'kill_streak': kill_streak,
                'round_kills': round_kills,
                'score_ct': ct_score,
                'score_t': t_score,
                'is_ct': is_ct,
                'economy_status': SmartContextBuilder._get_economy_status(money),
            }
            
            logger.debug(f"[CONTEXT] ✅ Контекст: HP={hp}, KS={kill_streak}, Ammo={mag}/{reserve}")
            return context
        
        except Exception as e:
            logger.error(f"[CONTEXT] ❌ Ошибка: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def _get_economy_status(money: int) -> str:
        """
        Определить статус экономики в раунде
        
        Args:
            money: Количество денег у игрока
        
        Returns:
            Статус: fullbuy, eco, half_eco или save
        """
        if money >= 2400:
            return "fullbuy"  # Полная покупка оружия
        elif money >= 1900:
            return "eco"      # Эконом раунд с покупкой
        elif money >= 1200:
            return "half_eco" # Полу-экономический раунд
        else:
            return "save"     # Экономия денег
