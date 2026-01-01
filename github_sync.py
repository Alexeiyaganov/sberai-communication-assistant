#!/usr/bin/env python3
"""
Простой скрипт для синхронизации с GitHub: pull -> изменения -> commit -> push
"""

import os
import sys
from datetime import datetime

def github_sync():
    """Полная синхронизация с GitHub"""
    
    print("🔄 СИНХРОНИЗАЦИЯ С GITHUB")
    print("="*50)
    
    # 1. Настройка пользователя
    print("\n1. ⚙️  Настройка Git...")
    os.system('git config --global user.name "Alexeiyaganov"')
    os.system('git config --global user.email "btls3@yandex.ru"')
    
    # 2. Получаем токен
    print("\n2. 🔑 Получение GitHub токена...")
    token = None
    
    # Пробуем из переменных окружения
    token = os.environ.get('GITHUB_TOKEN')
    
    # Или из Colab Secrets
    if not token:
        try:
            from google.colab import userdata
            token = userdata.get('GITHUB_TOKEN')
        except:
            pass
    
    # Или запрашиваем вручную
    if not token:
        print("\n📝 Введите GitHub Personal Access Token:")
        print("(Создайте на: https://github.com/settings/tokens)")
        token = input("Token: ").strip()
        if token:
            os.environ['GITHUB_TOKEN'] = token
    
    if not token:
        print("❌ Токен не найден!")
        return False
    
    # 3. Настраиваем remote URL с токеном
    print("\n3. 🔗 Настройка подключения к GitHub...")
    repo_url = f"https://Alexeiyaganov:{token}@github.com/Alexeiyaganov/sberai-personal-assistant.git"
    
    # Устанавливаем или обновляем remote
    result = os.system(f'git remote set-url origin {repo_url}')
    if result != 0:
        os.system(f'git remote add origin {repo_url}')
    
    # 4. PULL - получаем последние изменения
    print("\n4. 📥 Получение последних изменений с GitHub...")
    pull_result = os.system('git pull origin main')
    
    if pull_result != 0:
        print("⚠️  Возможно это новый репозиторий или проблемы с подключением")
    
    # 5. Показываем статус
    print("\n5. 📊 Текущий статус Git:")
    os.system('git status')
    
    print("\n" + "="*50)
    print("✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*50)
    
    return True

if __name__ == "__main__":
    github_sync()
