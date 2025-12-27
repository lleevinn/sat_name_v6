#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_server_examples.py - Набор тестов для iris_server.py

Открой терминал второе, запусти iris_server.py, потом этот скрипт:
    python iris_ai/test_server_examples.py
"""

import requests
import json
from typing import Dict, Any

# Настройки
BASE_URL = "http://localhost:5000"
COLOR_GREEN = "\033[92m"
COLOR_BLUE = "\033[94m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"

def colored(text: str, color: str) -> str:
    """Colors text for terminal output."""
    return f"{color}{text}{COLOR_RESET}"

def test_health():
    """Test GET /health endpoint."""
    print(f"\n{colored('TEST: /health (проверить сервер)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print(colored("✅ PASSED", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_info():
    """Test GET /info endpoint."""
    print(f"\n{colored('TEST: /info (информация о IRIS)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/info")
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and result.get('status') == 'running':
            print(colored("✅ PASSED", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_event_kill():
    """Test POST /event with kill event."""
    print(f"\n{colored('TEST: /event (убийство - AWP x3)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "type": "kill",
            "kills": 3,
            "weapon": "AWP"
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/event", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and 'response' in result:
            print(colored(f"✅ IRIS сказала: {result['response']}", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_event_death():
    """Test POST /event with death event."""
    print(f"\n{colored('TEST: /event (смерть от врага)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "type": "death",
            "killer": "Enemy's Ace"
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/event", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and 'response' in result:
            print(colored(f"✅ IRIS сказала: {result['response']}", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_event_achievement():
    """Test POST /event with achievement event."""
    print(f"\n{colored('TEST: /event (достижение - пентакилл)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "type": "achievement",
            "name": "Пентакилл"
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/event", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and 'response' in result:
            print(colored(f"✅ IRIS сказала: {result['response']}", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_event_low_health():
    """Test POST /event with low_health event."""
    print(f"\n{colored('TEST: /event (низкое здоровье - 25 HP)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "type": "low_health",
            "health": 25
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/event", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and 'response' in result:
            print(colored(f"✅ IRIS сказала: {result['response']}", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_say():
    """Test POST /say endpoint."""
    print(f"\n{colored('TEST: /say (произвольный вопрос)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "text": "Как помочь нашей команде выиграть?"
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/say", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and 'response' in result:
            print(colored(f"✅ IRIS ответила: {result['response']}", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_context_get():
    """Test GET /context endpoint."""
    print(f"\n{colored('TEST: /context GET (получить контекст)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/context")
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Context Length: {result.get('context_length')}")
        print(f"Last Messages: {json.dumps(result.get('context', []), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print(colored("✅ PASSED", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def test_context_post():
    """Test POST /context endpoint."""
    print(f"\n{colored('TEST: /context POST (добавить в контекст)', COLOR_BLUE)}")
    print("-" * 50)
    
    try:
        data = {
            "role": "user",
            "content": "Привет IRIS, как твой день?"
        }
        
        print(f"Sending: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(f"{BASE_URL}/context", json=data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print(colored("✅ PASSED", COLOR_GREEN))
            return True
        else:
            print(colored("❌ FAILED", COLOR_RED))
            return False
    
    except Exception as e:
        print(colored(f"❌ ERROR: {e}", COLOR_RED))
        return False

def main():
    """
    Запустить все тесты.
    """
    print(f"{colored('='*60, COLOR_YELLOW)}")
    print(f"{colored('[TEST SUITE] IRIS Server Endpoint Tests', COLOR_YELLOW)}")
    print(f"{colored('='*60, COLOR_YELLOW)}")
    
    # Проверяем что сервер доступен
    print(f"\n{colored('Проверка подключения к серверу...', COLOR_YELLOW)}")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(colored("✅ Сервер доступен!", COLOR_GREEN))
    except Exception as e:
        print(colored(f"❌ Сервер недоступен: {e}", COLOR_RED))
        print(f"\n{colored('Убедись что iris_server.py запущена!', COLOR_RED)}")
        print(f"   python iris_ai/iris_server.py")
        return
    
    # Запускаем тесты
    tests = [
        test_health,
        test_info,
        test_event_kill,
        test_event_death,
        test_event_achievement,
        test_event_low_health,
        test_say,
        test_context_get,
        test_context_post,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(colored(f"❌ Test crashed: {e}", COLOR_RED))
            results.append(False)
    
    # Результаты
    print(f"\n{colored('='*60, COLOR_YELLOW)}")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(colored(f"✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! {passed}/{total}", COLOR_GREEN))
    else:
        print(colored(f"⚠️  ПРОВАЛЕНО: {passed}/{total} тестов", COLOR_YELLOW))
    
    print(f"{colored('='*60, COLOR_YELLOW)}")
    print(f"{colored('IRIS ГОТОВА К СТРИМУ! 🚀', COLOR_GREEN)}")

if __name__ == "__main__":
    main()
