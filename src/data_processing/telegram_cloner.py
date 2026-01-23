#!/usr/bin/env python3
"""
Клонер диалогов через Telegram API для извлечения вашего стиля общения
"""

import asyncio
from telethon import TelegramClient
from telethon.tl.types import Message, User, Chat, Channel
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Optional
import re


class TelegramStyleCloner:
    """Клонирует ваш стиль общения из Telegram"""

    def __init__(self, config):
        self.config = config
        self.api_id = config.telegram.api_id
        self.api_hash = config.telegram.api_hash
        self.phone = config.telegram.phone
        self.session_name = config.telegram.session_name

        # Директории для данных
        self.cloned_dir = Path(config.paths.cloned_data)
        self.style_profiles_dir = Path(config.paths.style_profiles)
        self.cloned_dir.mkdir(parents=True, exist_ok=True)
        self.style_profiles_dir.mkdir(parents=True, exist_ok=True)

        self.client = None

    async def connect(self):
        """Подключается к Telegram"""
        print("🔗 Подключение к Telegram...")
        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash,
            device_model="Personal Communication Assistant",
            system_version="1.0",
            app_version="1.0.0"
        )

        await self.client.start(phone=self.phone)
        print("✅ Подключение успешно")
        return self.client

    async def analyze_dialog_context(self, dialog) -> str:
        """Анализирует контекст диалога"""
        dialog_name = dialog.name or dialog.title or "Unknown"

        # Определяем тип диалога
        if dialog.is_user:
            # Личный диалог
            user = await self.client.get_entity(dialog.entity)
            if hasattr(user, 'username'):
                return f"personal_{user.username or 'user'}"
            return "personal"

        elif dialog.is_group:
            # Групповой чат
            if "семья" in dialog_name.lower() or "family" in dialog_name.lower():
                return "family"
            elif "работа" in dialog_name.lower() or "work" in dialog_name.lower():
                return "professional"
            elif any(word in dialog_name.lower() for word in ["друзья", "friends", "тусовка"]):
                return "friendly"
            else:
                return "group"

        elif dialog.is_channel:
            return "channel"

        return "unknown"

    async def extract_my_messages(self, dialog, context: str, limit: int = 1000) -> List[Dict]:
        """Извлекает мои сообщения из диалога"""
        my_messages = []

        try:
            # Получаем мой ID
            me = await self.client.get_me()
            my_id = me.id

            async for message in self.client.iter_messages(dialog, limit=limit):
                # Проверяем, что это мое сообщение
                if not message.sender or message.sender.id != my_id:
                    continue

                # Пропускаем пустые сообщения
                if not message.text or len(message.text.strip()) < 2:
                    continue

                # Пропускаем служебные сообщения
                if message.text.startswith('```') or message.text.startswith('/'):
                    continue

                # Получаем контекст (предыдущие сообщения)
                context_messages = await self._get_message_context(message, dialog)

                msg_data = {
                    'text': message.text,
                    'date': message.date.isoformat() if message.date else None,
                    'message_id': message.id,
                    'dialog_id': dialog.id,
                    'dialog_name': dialog.name or dialog.title,
                    'context_type': context,
                    'context_messages': context_messages,
                    'has_media': bool(message.media),
                    'message_type': self._classify_message_type(message.text)
                }

                my_messages.append(msg_data)

        except Exception as e:
            print(f"Ошибка при извлечении сообщений: {e}")

        return my_messages

    async def _get_message_context(self, message, dialog, num_context: int = 3) -> List[str]:
        """Получает контекст для сообщения"""
        context_messages = []

        try:
            # Получаем сообщения перед текущим
            async for prev_msg in self.client.iter_messages(
                    dialog,
                    limit=num_context,
                    offset_id=message.id,
                    reverse=True
            ):
                if prev_msg.id == message.id:
                    continue

                if prev_msg.text and len(prev_msg.text.strip()) > 1:
                    sender_prefix = "Я: " if prev_msg.sender and prev_msg.sender.id == message.sender.id else "Собеседник: "
                    context_messages.append(f"{sender_prefix}{prev_msg.text}")

        except:
            pass

        return context_messages

    def _classify_message_type(self, text: str) -> str:
        """Классифицирует тип сообщения"""
        text_lower = text.lower()

        # Вопросы
        if text.endswith('?') or any(word in text_lower for word in ['как', 'что', 'где', 'когда', 'почему']):
            return 'question'

        # Восклицания
        if text.endswith('!') or any(word in text_lower for word in ['класс', 'отлично', 'супер', 'ура']):
            return 'exclamation'

        # Короткие сообщения
        if len(text.split()) <= 3:
            return 'short'

        # Длинные сообщения
        if len(text.split()) > 20:
            return 'long'

        # Сообщения с эмодзи
        if any(emoji in text for emoji in ['😀', '😂', '😊', '😍', '😎', '🤔', '👍']):
            return 'with_emoji'

        return 'normal'

    async def clone_my_style(self):
        """Клонирует мой стиль общения из всех диалогов"""
        print("\n🎭 КЛОНИРОВАНИЕ ВАШЕГО СТИЛЯ ОБЩЕНИЯ")
        print("=" * 50)

        client = await self.connect()

        try:
            print("📁 Получение списка диалогов...")
            dialogs = await client.get_dialogs(limit=50)

            all_my_messages = []
            context_stats = {}

            for dialog in dialogs:
                # Анализируем контекст диалога
                context = await self.analyze_dialog_context(dialog)
                dialog_name = dialog.name or dialog.title or f"Dialog_{dialog.id}"

                print(f"\n📨 Диалог: {dialog_name} ({context})")

                # Извлекаем мои сообщения
                messages = await self.extract_my_messages(
                    dialog,
                    context,
                    limit=self.config.telegram.max_messages_per_dialog
                )

                if messages:
                    all_my_messages.extend(messages)

                    # Обновляем статистику
                    if context not in context_stats:
                        context_stats[context] = 0
                    context_stats[context] += len(messages)

                    print(f"   📝 Моих сообщений: {len(messages)}")

                    # Сохраняем отдельно для этого диалога
                    dialog_file = self.cloned_dir / f"dialog_{dialog.id}_{context}.json"
                    with open(dialog_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'dialog_id': dialog.id,
                            'dialog_name': dialog_name,
                            'context': context,
                            'messages': messages,
                            'export_date': datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)

            # Сохраняем все сообщения
            if all_my_messages:
                # Основной файл
                main_file = self.cloned_dir / "my_communication_style.json"
                with open(main_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'total_messages': len(all_my_messages),
                        'context_stats': context_stats,
                        'export_date': datetime.now().isoformat(),
                        'messages': all_my_messages
                    }, f, ensure_ascii=False, indent=2)

                # Создаем профиль стиля
                style_profile = self.create_style_profile(all_my_messages)

                print(f"\n✅ Клонирование завершено!")
                print(f"📊 Всего сообщений: {len(all_my_messages)}")
                print(f"📁 Контексты: {context_stats}")
                print(f"💾 Сохранено в: {main_file}")
                print(f"🎭 Профиль стиля создан: {style_profile}")

                return main_file, style_profile
            else:
                print("❌ Не найдено ваших сообщений")
                return None, None

        finally:
            await client.disconnect()

    def create_style_profile(self, messages: List[Dict]) -> Path:
        """Создает профиль стиля общения"""
        print("\n🎨 Анализ вашего стиля общения...")

        # Анализируем стиль
        style_analysis = {
            'average_message_length': 0,
            'emoji_frequency': 0,
            'question_frequency': 0,
            'exclamation_frequency': 0,
            'word_usage': {},
            'context_preferences': {},
            'message_type_distribution': {}
        }

        total_messages = len(messages)

        for msg in messages:
            text = msg['text']

            # Длина сообщения
            words = text.split()
            style_analysis['average_message_length'] += len(words)

            # Эмодзи
            if any(emoji in text for emoji in ['😀', '😂', '😊', '😍', '😎']):
                style_analysis['emoji_frequency'] += 1

            # Вопросы
            if '?' in text:
                style_analysis['question_frequency'] += 1

            # Восклицания
            if '!' in text:
                style_analysis['exclamation_frequency'] += 1

            # Тип сообщения
            msg_type = msg.get('message_type', 'normal')
            if msg_type not in style_analysis['message_type_distribution']:
                style_analysis['message_type_distribution'][msg_type] = 0
            style_analysis['message_type_distribution'][msg_type] += 1

            # Контекст
            context = msg.get('context_type', 'unknown')
            if context not in style_analysis['context_preferences']:
                style_analysis['context_preferences'][context] = 0
            style_analysis['context_preferences'][context] += 1

            # Частые слова (без стоп-слов)
            common_words = self._extract_common_words(text)
            for word in common_words:
                if word not in style_analysis['word_usage']:
                    style_analysis['word_usage'][word] = 0
                style_analysis['word_usage'][word] += 1

        # Вычисляем средние значения
        if total_messages > 0:
            style_analysis['average_message_length'] /= total_messages
            style_analysis['emoji_frequency'] /= total_messages
            style_analysis['question_frequency'] /= total_messages
            style_analysis['exclamation_frequency'] /= total_messages

        # Сохраняем профиль
        profile_file = self.style_profiles_dir / "my_style_profile.json"

        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_date': datetime.now().isoformat(),
                'total_messages_analyzed': total_messages,
                'style_analysis': style_analysis,
                'summary': self._create_style_summary(style_analysis)
            }, f, ensure_ascii=False, indent=2)

        return profile_file

    def _extract_common_words(self, text: str, min_length: int = 3) -> List[str]:
        """Извлекает частые слова"""
        # Убираем пунктуацию и приводим к нижнему регистру
        words = re.findall(r'\b[а-яё]{3,}\b', text.lower())

        # Стоп-слова для русского языка
        stop_words = {'это', 'как', 'так', 'и', 'в', 'над', 'к', 'до', 'не', 'на', 'но', 'за', 'то',
                      'с', 'ли', 'а', 'во', 'от', 'со', 'для', 'о', 'же', 'ну', 'вы', 'бы', 'что',
                      'кто', 'он', 'она'}

        return [word for word in words if word not in stop_words]

    def _create_style_summary(self, analysis: Dict) -> Dict:
        """Создает сводку по стилю"""
        summary = {
            'message_length': 'Короткие' if analysis['average_message_length'] < 5 else
            'Средние' if analysis['average_message_length'] < 15 else 'Длинные',
            'emoji_usage': 'Редко' if analysis['emoji_frequency'] < 0.1 else
            'Умеренно' if analysis['emoji_frequency'] < 0.3 else 'Часто',
            'question_style': 'Мало вопросов' if analysis['question_frequency'] < 0.1 else
            'Умеренно вопросов' if analysis['question_frequency'] < 0.3 else 'Много вопросов',
            'emotionality': 'Сдержанный' if analysis['exclamation_frequency'] < 0.1 else
            'Эмоциональный' if analysis['exclamation_frequency'] < 0.3 else 'Очень эмоциональный'
        }

        # Самые частые контексты
        if analysis['context_preferences']:
            top_contexts = sorted(
                analysis['context_preferences'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            summary['top_contexts'] = [ctx for ctx, _ in top_contexts]

        # Самые частые слова
        if analysis['word_usage']:
            top_words = sorted(
                analysis['word_usage'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            summary['top_words'] = [word for word, _ in top_words]

        return summary


def main():
    """Точка входа для клонирования стиля"""
    import yaml
    from pathlib import Path

    # Загружаем конфигурацию
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("❌ Файл конфигурации не найден")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Запускаем клонирование
    print("🚀 Запуск клонирования вашего стиля общения...")

    cloner = TelegramStyleCloner(config_dict)

    try:
        asyncio.run(cloner.clone_my_style())
    except KeyboardInterrupt:
        print("\n👋 Клонирование прервано")
    except Exception as e:
        print(f"❌ Ошибка клонирования: {e}")


if __name__ == "__main__":
    main()