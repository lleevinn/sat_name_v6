"""
Qwen3 AI Module для IRIS
Локальное LLM через Ollama
"""

import logging
from typing import Optional

try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

logger = logging.getLogger("QwenAI")


class QwenAI:
    """Интеграция локального Qwen3 AI"""
    
    def __init__(self, model: str = "qwen3:4b-instruct", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.client = None
        self.available = False
        
        self._initialize()
    
    def _initialize(self):
        """Инициализация Ollama клиента"""
        if not OLLAMA_AVAILABLE:
            logger.warning("[QWEN] Ollama не установлена. pip install ollama")
            return
        
        try:
            self.client = OllamaClient(host=self.host)
            
            # Тест доступности
            response = self.client.generate(
                model=self.model,
                prompt="Hi",
                stream=False,
                keep_alive=0
            )
            
            self.available = True
            logger.info(f"[QWEN] ✅ Инициализирована модель {self.model}")
        
        except Exception as e:
            logger.error(f"[QWEN] ❌ Ошибка инициализации: {e}")
            self.available = False
    
    def iris_chat(self, command: str, max_tokens: int = 100) -> Optional[str]:
        """Ответить как Ирис на голосовую команду"""
        if not self.available or not self.client:
            return None
        
        try:
            system_prompt = """Ты Ирис - дружелюбный и эмоциональный AI помощник для стриминга CS2.
Отвечай коротко (1 предложение, максимум 15 слов).
Будь позитивной и веселой.
Используй эмодзи когда уместно."""
            
            full_prompt = f"{system_prompt}\n\nПользователь: {command}\nИрис:"
            
            # ✅ БЕЗ temperature, num_predict и других параметров
            response = self.client.generate(
                model=self.model,
                prompt=full_prompt,
                stream=False
            )
            
            text = response.get('response', '').strip()
            
            if text and len(text) > 2:
                logger.info(f"[QWEN] 🤖 Ответ: {text[:100]}...")
                return text
            
            return None
        
        except Exception as e:
            logger.error(f"[QWEN] Ошибка: {e}")
            return None

    
    def is_available(self) -> bool:
        """Проверить доступность AI"""
        return self.available
