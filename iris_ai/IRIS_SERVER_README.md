# 🙋 IRIS Server - ДОЛГОЖИВУЩИЙ FLASK СЕРВЕР

Вторая жизнь IRIS! 🚀

## Очем это?

**Проблема истара:** 
- `iris_main.py` - тестовый скрипт, запускается и тестирует IRIS, потом выходит. Не подходит для стрима!

**Решение радикальное:** 
- `iris_server.py` - долгоживущий Flask сервер, который:
  - НиИЗ (запускается один раз)
  - Остаётся включённым всё время стрима
  - Принимает события дюю через HTTP POST
  - Отвечает оттуда же

---

## ✈️ Быстрый старт (5 мин)

### Шаг 1: Проверь Ollama

```bash
# Открой терминал другое окно
 ollama serve
```

### Шаг 2: Проверь Модель

```bash
# Если модель ещё не загружена:
ollama run qwen3:4b-instruct
```

### Шаг 3: Запусти IRIS Server

```bash
python iris_ai/iris_server.py
```

Ожидаемые логи:
```
==================================================
[IRIS] ЗАПУСК ДОЛГОЖИВУЩЕГО СЕРВЕРА
==================================================
[IRIS] Инициализирую IRIS...
[IRIS] ✅ Успешно инициализирована!
[SERVER] 🚀 Сервер доступен на http://localhost:5000
[SERVER] IRIS готова! Ожидаю события...
```

**ДОНЕ! 🎉 IRIS работает!**

---

## 🧨 Эндпоинты (ресты)

### `GET /health` - Проверить если сервер жив

```bash
curl http://localhost:5000/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "iris": "ready",
  "timestamp": "2025-12-27T21:00:00"
}
```

---

### `POST /event` - Отправить игровое событие

Работает четыре типа событий: `kill`, `death`, `achievement`, `low_health`

#### Поган:
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "type": "kill",
    "kills": 3,
    "weapon": "AWP"
  }'
```

**Ответ:**
```json
{
  "status": "ok",
  "event": "kill",
  "response": "Ого, три убийства подряд — это дело! Молодец!!",
  "timestamp": "2025-12-27T21:00:05"
}
```

#### Мертвый:
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "type": "death",
    "killer": "Ес выборы"
  }'
```

#### Достижение:
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "type": "achievement",
    "name": "Пентакилл"
  }'
```

#### Писклявание здоровье:
```bash
curl -X POST http://localhost:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "type": "low_health",
    "health": 25
  }'
```

---

### `POST /say` - Генерировать ответ на произвольный текст

```bash
curl -X POST http://localhost:5000/say \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Как твои дела, IRIS?"
  }'
```

**Ответ:**
```json
{
  "status": "ok",
  "input": "Как твои дела, IRIS?",
  "response": "Всё системов в порядке, бру! Говорют о победе в офф-тайм?",
  "timestamp": "2025-12-27T21:00:10"
}
```

---

### `GET /info` - Информация о IRIS

```bash
curl http://localhost:5000/info
```

**Ответ:**
```json
{
  "name": "IRIS",
  "version": "1.0",
  "model": "qwen3:4b-instruct",
  "temperature": 0.8,
  "max_tokens": 150,
  "status": "running",
  "uptime": "2025-12-27T21:00:15"
}
```

---

### `GET /context` - Получить опыты разговора

```bash
curl http://localhost:5000/context
```

**Ответ:**
```json
{
  "context_length": 3,
  "context": [
    {"role": "user", "content": "Помоги!", "timestamp": "2025-12-27T21:00:20"},
    {"role": "iris", "content": "Я здесь!", "timestamp": "2025-12-27T21:00:25"}
  ]
}
```

### `POST /context` - Добавить разговор в контекст

```bash
curl -X POST http://localhost:5000/context \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "Новые раунды начинаются"
  }'
```

---

## 🌯 Python API (в коде)

Это для тех, кто хочет страймирать сервер от другого скрипта:

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# Проверить сервер
response = requests.get(f"{BASE_URL}/health")
if response.status_code == 200:
    print("✅ Сервер в порядке")

# Отправить событие
data = {"type": "kill", "kills": 2, "weapon": "Deagle"}
response = requests.post(f"{BASE_URL}/event", json=data)
result = response.json()
print(f"IRIS: {result['response']}")

# Попросить ответ
data = {"text": "На подмога?"}
response = requests.post(f"{BASE_URL}/say", json=data)
result = response.json()
print(f"IRIS: {result['response']}")
```

---

## 📚 Пример интеграции с обстримом (CS2)

### 1. Поставь конфиг:
```
C:\Program Files\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\gamestate_integration_iris.cfg
```

### 2. Читать GSI в другом скрипте:
```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests

class GSIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(length))
        
        # Парсим эвенты
        if data['player']['state'].get('health', 100) < 30:
            requests.post('http://localhost:5000/event', json={
                'type': 'low_health',
                'health': data['player']['state']['health']
            })
        
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('localhost', 3000), GSIHandler)
    print("🚣 GSI сервер на :3000")
    server.serve_forever()
```

---

## 🏧 Не работает?

### "Сервер отключается"
- Проверь Ollama: `ollama serve` в другом терминале
- Проверь модель: `ollama run qwen3:4b-instruct`

### "Ответы пустые"
- Подожди 2-3 секунды (LLM медленная)
- Проверь `iris_server.log` в основной папке

### "Порт 5000 занят"
```bash
# Найти процесс
lsof -i :5000
# Kill
kill -9 <PID>
```

---

## 🌟 Что дальше?

- Поставь **TTS** (синтез речи) - можно добавить Edge TTS
- Поставь **аудио эффекты** - Фанфары, сирены, эмоуциональные жесты
- Поставь **OBS интеграцию** - видео/аудио стрима
- Оптимизировать **Промпты** - содержание ответов

---

**Финал: IRIS теперь воеждит в фоне! 🚀🙋**
