"""
IRIS BRAIN v2.1 - ЭНТО НЕ БОТ, ЭТО ЛИЧНОСТЬ!
LLM генерирует ВСЕ фразы в real-time
context_builder ОНЛЫ снабжает инфо о ситуации
"""

from typing import Dict, Optional, List
from datetime import datetime
from collections import deque
import asyncio
import logging

# Модули
from context_builder_v2 import SmartContextBuilder, GameContext, SituationType
from iris_smart_engine import EventPriorityManager, EventPriority
from tts_engine import TTSEngine
from iris_voice_engine import IrisVoiceEngine

from groq import Groq

logger = logging.getLogger(__name__)


class IrisBrainV2:
    """
    НОВАЯ АРХИТЕКТУРА:
    - context_builder: АНАЛИЗИРУЕТ ситуацию
    - LLM (Groq): ГЕНЕРИРУЕТ ФРАЗЫ
    - tts_engine: ОЗВУЧИВАЕТ
    
    НИКАКОГО МУСОРА, НИКАКОГО скрипта!
    """
    
    def __init__(self):
        self.context_builder = SmartContextBuilder()
        self.smart_engine = EventPriorityManager()
        self.tts_engine = TTSEngine()
        self.voice_engine = IrisVoiceEngine()
        
        self.groq_client = Groq()  # ОПТ из енва
        self.model = "mixtral-8x7b-32768"
        
        self.conversation_history = deque(maxlen=20)
        self.recent_game_events = deque(maxlen=10)
        self.last_spoken_time = None
        self.can_speak_again = True
        self.is_running = False
        
    def start(self):
        self.is_running = True
        logger.info("✅ IRIS Brain v2.1 запущена")
        
    def stop(self):
        self.is_running = False
        self.tts_engine.flush()
        logger.info("❤ IRIS Brain v2.1 остановлена")
    
    # ============================================================
    # ГЛАВНАЯ ОБРАБОТКА
    # ============================================================
    
    def react_to_event(self, player, cs2_gsi, event_type: str, event_data: Dict) -> Optional[str]:
        """
        1. context_builder -> ситуация
        2. LLM -> фраза
        3. TTS -> начинает говорить
        """
        
        if not self.is_running:
            return None
        
        try:
            context = self.context_builder.build(player, cs2_gsi, event_type, event_data)
            priority = self.smart_engine.get_priority(event_type, {
                'health': context.health,
                'ammo': context.ammo_total,
                'kill_streak': context.kill_streak,
                'round_kills': context.round_kills,
            })
            
            if priority == EventPriority.IGNORE:
                return None
            
            if priority != EventPriority.CRITICAL and not self.can_speak_again:
                return None
            
            if priority == EventPriority.CRITICAL:
                self.tts_engine.interrupt()
            
            # ✨ ЛЛМ ГЕНЕРИРУЕТ ФРАЗУ
            response = self._generate_from_llm(event_type, context, priority)
            
            if not response or response == "SKIP":
                return None
            
            self.conversation_history.append({
                'timestamp': datetime.now(),
                'event': event_type,
                'response': response,
                'priority': priority.name
            })
            self.recent_game_events.append({'type': event_type, 'data': event_data})
            
            emotion = self._detect_emotion(event_type, context, priority)
            self._speak(response, emotion=emotion, priority=priority)
            self._update_cooldown(priority)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    # ============================================================
    # ✨ LLM ГЕНЕРАЦИЯ
    # ============================================================
    
    def _generate_from_llm(self, event_type: str, context: GameContext, 
                          priority: EventPriority) -> Optional[str]:
        """
        ✨ НЮХОВОЙ МОМЕНТ ✨
        LLM генерирует респонс
        """
        
        system = f"""Ты IRIS - ЛОЧНОСТЬ в CS2.
Правила:
- Ответ МАКС 1-2 предложения (TTS будет озвучивать)
- НИКАКОГО мусора из скриптов!
- ГЕНЕРИРУЙ ПО НОВОМУ каждый раз
- Естественная русская речь
- На критичных - срочно и чётко
- Если нечего сказать - верни SKIP
"""
        
        user = f"""СИТУАЦИя: {event_type} ({priority.name})

{context.situation_description}

Принятая действия - говори что-нибудь или SKIP:
"""
        
        try:
            resp = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.9,
                max_tokens=150,
                top_p=0.95,
            )
            
            text = resp.choices[0].message.content.strip()
            return text if len(text) > 3 else None
            
        except Exception as e:
            logger.error(f"LLM ошибка: {e}")
            return None
    
    def _detect_emotion(self, event_type: str, context: GameContext, 
                       priority: EventPriority) -> str:
        """Emotion для TTS"""
        
        if priority == EventPriority.CRITICAL:
            return 'tense'
        
        if event_type == 'kill':
            if context.round_kills >= 5:
                return 'excited'
            elif context.round_kills >= 3:
                return 'happy'
            else:
                return 'calm'
        
        if event_type == 'death':
            return 'supportive'
        
        if context.kill_streak >= 10:
            return 'proud'
        
        return 'neutral'
    
    def _speak(self, text: str, emotion: str = 'neutral', priority: EventPriority = EventPriority.MEDIUM):
        """TTS"""
        try:
            self.tts_engine.speak(
                text=text,
                emotion=emotion,
                priority=(priority == EventPriority.CRITICAL)
            )
            self.last_spoken_time = datetime.now()
        except Exception as e:
            logger.error(f"TTS ошибка: {e}")
    
    def _update_cooldown(self, priority: EventPriority):
        """Cooldown чтобы не надоедала"""
        if priority == EventPriority.CRITICAL:
            self.can_speak_again = True
        else:
            self.can_speak_again = False
            asyncio.create_task(self._reset_cooldown())
    
    async def _reset_cooldown(self):
        await asyncio.sleep(4)
        self.can_speak_again = True
    
    # ============================================================
    # ИТОН
    # ============================================================
    
    def react_to_kill(self, kill_data: Dict) -> Optional[str]:
        return self.react_to_event(
            player=kill_data.get('player'),
            cs2_gsi=kill_data.get('cs2_gsi'),
            event_type='kill',
            event_data=kill_data
        )
    
    def react_to_death(self, death_data: Dict) -> Optional[str]:
        return self.react_to_event(
            player=death_data.get('player'),
            cs2_gsi=death_data.get('cs2_gsi'),
            event_type='death',
            event_data=death_data
        )
