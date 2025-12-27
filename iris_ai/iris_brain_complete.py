#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iris_brain_complete.py - ПОЛНЫЙ МОЗ IRIS AI
"""

import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class IrisAI:
    """IRIS - AI мозг для CS2 стримера."""
    
    def __init__(
        self,
        model: str = "qwen3:4b-instruct",
        temperature: float = 0.8,
        max_tokens: int = 150,
        ollama_host: str = "http://localhost:11434",
        debug: bool = False
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.ollama_host = ollama_host
        self.debug = debug
        
        try:
            import ollama
            self.ollama_client = ollama.Client(host=ollama_host)
            logger.info(f"Ollama клиент инициализирован: {ollama_host}")
        except Exception as e:
            logger.error(f"Ошибка инициализации Ollama: {e}")
            self.ollama_client = None
        
        self.context = []
        self.game_events = []
        
        if debug:
            logger.debug(f"IRIS инициализирована: модель={model}, temp={temperature}")
    
    def generate_response(
        self,
        prompt: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Генерировать ответ через Ollama LLM.
        """
        try:
            _model = model or self.model
            _temperature = temperature if temperature is not None else self.temperature
            _max_tokens = max_tokens or self.max_tokens
            
            if self.debug:
                logger.debug(f"Генерирую ответ: модель={_model}")
            
            response = self.ollama_client.generate(
                model=_model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": _temperature,
                    "num_predict": _max_tokens
                }
            )
            
            text = response.get('response', '').strip()
            if self.debug:
                logger.debug(f"LLM Response: {text}")
            
            return text
        
        except Exception as e:
            logger.error(f"Ошибка генерации LLM: {e}")
            return "Ооп, мозг не работает. Попробуй ещё раз!"
    
    def analyze_game_event(self, event_type: str, details: Dict[str, Any]) -> str:
        """
        Анализировать игровое событие и сгенерировать комментарий IRIS.
        """
        self.game_events.append({
            'type': event_type,
            'details': details,
            'timestamp': datetime.now()
        })
        
        prompt = self._create_event_prompt(event_type, details)
        return self.generate_response(prompt)
    
    def _create_event_prompt(self, event_type: str, details: Dict) -> str:
        """
        Создать промпт для анализа события.
        """
        base = "Ты IRIS - смешной, саркастичный AI помощник CS2 стримера. Отвечай коротко (1-2 предложения) на русском.\n\n"
        
        if event_type == "kill":
            kills = details.get('kills', 1)
            weapon = details.get('weapon', 'неизвестное оружие')
            return f"{base}Игрок только что убил {kills} врага(ов) оружием {weapon}. Как бы ты это прокомментировал?"
        
        elif event_type == "death":
            killer = details.get('killer', 'кто-то')
            return f"{base}Игрока только что убил {killer}. Как утешить игрока?"
        
        elif event_type == "achievement":
            achievement = details.get('name', 'неизвестное достижение')
            return f"{base}Игрок разблокировал достижение: {achievement}. Как бы ты это отреагировал?"
        
        elif event_type == "low_health":
            health = details.get('health', 0)
            return f"{base}У игрока осталось {health} HP! Как срочно его предупредить?"
        
        else:
            return f"{base}Произошло событие: {event_type}. {details}"
    
    def add_context(self, message: str, role: str = "user"):
        """
        Добавить сообщение в контекст разговора.
        """
        self.context.append({
            'role': role,
            'content': message,
            'timestamp': datetime.now()
        })
        
        if self.debug:
            logger.debug(f"Context добавлено: {role} - {message[:50]}...")
    
    def get_context_prompt(self) -> str:
        """
        Получить полный контекст для промпта.
        """
        if not self.context:
            return ""
        
        context_str = "История разговора:\n"
        for msg in self.context[-5:]:
            role = msg['role'].upper()
            context_str += f"{role}: {msg['content']}\n"
        
        return context_str
    
    def test_connection(self) -> bool:
        """
        Проверить соединение с Ollama.
        """
        try:
            response = self.ollama_client.generate(
                model=self.model,
                prompt="test",
                stream=False,
                options={"num_predict": 1}
            )
            logger.info(f"Соединение с Ollama успешно: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Ошибка соединения с Ollama: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    iris = IrisAI(debug=True)
    
    if iris.test_connection():
        response = iris.generate_response(
            "Ты IRIS. Ответь коротко: какой твой любимый weapon в CS2?"
        )
        print(f"Ответ IRIS: {response}")
        
        event_response = iris.analyze_game_event(
            "kill",
            {'kills': 3, 'weapon': 'AWP'}
        )
        print(f"Комментарий события: {event_response}")
    else:
        print("Не могу подключиться к Ollama!")
