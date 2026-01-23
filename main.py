#!/usr/bin/env python3
"""
Personal Communication Assistant - Основной скрипт
"""

import argparse
import yaml
from pathlib import Path
import sys

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / "src"))


def clone_my_style(config):
    """Клонирует стиль общения из Telegram"""
    from data_processing.telegram_cloner import TelegramStyleCloner
    import asyncio

    print("🎭 Клонирование вашего стиля общения из Telegram...")

    cloner = TelegramStyleCloner(config)

    try:
        result = asyncio.run(cloner.clone_my_style())

        if result[0]:
            print(f"\n✅ Ваш стиль общения успешно проанализирован!")
            print(f"📁 Данные сохранены в: {result[0]}")
            print(f"🎭 Профиль стиля: {result[1]}")
        else:
            print("❌ Не удалось клонировать стиль")

    except Exception as e:
        print(f"❌ Ошибка клонирования: {e}")


def train_personal_model(config):
    """Обучает персонализированную модель"""
    from model.personal_trainer import PersonalizedStyleTrainer

    print("🎯 Обучение персонализированной модели...")

    try:
        trainer = PersonalizedStyleTrainer(config)
        results = trainer.train()

        if results:
            print(f"\n✅ Модель успешно обучена!")
            print(f"🎭 Обучено адаптеров: {len(results.get('context_adapters', {}))} контекстов")
            print(f"📁 Результаты в: {config.paths.adapters_dir}")

    except Exception as e:
        print(f"❌ Ошибка обучения: {e}")


def demo_assistant(config):
    """Демонстрация работы ассистента"""
    from model.response_generator import PersonalizedResponseGenerator
    from model.context_router import ContextRouter

    print("💬 Демонстрация Personal Communication Assistant")
    print("=" * 50)

    # Инициализируем компоненты
    generator = PersonalizedResponseGenerator(config)
    router = ContextRouter(config)

    # Примеры для разных контекстов
    examples = [
        {
            "context": "professional",
            "message": "Привет! Нужно обсудить проектную документацию по новому заказу",
            "history": ["Добрый день! Как успехи с проектом?"]
        },
        {
            "context": "family",
            "message": "Мама, я завтра приеду к вам на выходные",
            "history": ["Привет, сынок! Как дела?"]
        },
        {
            "context": "romantic",
            "message": "Любимый, я так по тебе скучаю ❤️",
            "history": ["Привет, дорогая! Как твой день?"]
        },
        {
            "context": "friendly",
            "message": "Привет! Давай сегодня вечером сходим в кино?",
            "history": ["Йоу! Что делаешь?"]
        },
        {
            "context": "creative",
            "message": "У меня родилась интересная идея для нового проекта!",
            "history": ["Привет! Что нового в творчестве?"]
        }
    ]

    for example in examples:
        print(f"\n{'=' * 40}")
        print(f"📝 Контекст: {example['context']}")
        print(f"💬 Сообщение: '{example['message']}'")

        # Определяем контекст
        route = router.route_context(
            example['message'],
            example['history']
        )

        print(f"🎯 Определен контекст: {route.primary_context} (уверенность: {route.confidence:.2f})")
        print(f"💡 Обоснование: {route.reasoning}")

        # Генерируем ответ
        responses = generator.generate_response(
            context=example['message'],
            dialog_history=example['history'],
            target_context=route.primary_context,
            num_options=2
        )

        if responses:
            print(f"\n💭 Варианты ответов:")
            for i, resp in enumerate(responses[:2], 1):
                print(f"{i}. [{resp['context_emoji']}] {resp['response']}")
        else:
            print("❌ Не удалось сгенерировать ответы")

    print(f"\n{'=' * 50}")
    print("🎉 Демонстрация завершена!")


def run_telegram_bot(config):
    """Запускает Telegram бота"""
    from bot.telegram_bot import CommunicationTelegramBot

    print("🤖 Запуск Telegram бота...")

    try:
        bot = CommunicationTelegramBot(config)
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")


def run_web_interface(config):
    """Запускает веб-интерфейс"""
    from bot.web_interface import CommunicationWebInterface

    print("🌐 Запуск веб-интерфейса...")

    try:
        interface = CommunicationWebInterface(config)
        interface.launch()
    except KeyboardInterrupt:
        print("\n👋 Интерфейс остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска интерфейса: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Personal Communication Assistant - Адаптивная модель общения"
    )

    parser.add_argument(
        "--mode",
        choices=["clone", "train", "demo", "bot", "web"],
        required=True,
        help="Режим работы"
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Путь к файлу конфигурации"
    )

    args = parser.parse_args()

    # Загружаем конфигурацию
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Файл конфигурации не найден: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Запускаем выбранный режим
    if args.mode == "clone":
        clone_my_style(config_dict)
    elif args.mode == "train":
        train_personal_model(config_dict)
    elif args.mode == "demo":
        demo_assistant(config_dict)
    elif args.mode == "bot":
        run_telegram_bot(config_dict)
    elif args.mode == "web":
        run_web_interface(config_dict)
    else:
        print(f"❌ Неизвестный режим: {args.mode}")


if __name__ == "__main__":
    main()