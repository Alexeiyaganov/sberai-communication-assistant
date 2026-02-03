#!/usr/bin/env python3
"""
Персонализированное обучение на основе вашего стиля общения
"""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import pandas as pd
from pathlib import Path
import json
from typing import Dict, List
import numpy as np


class PersonalizedStyleTrainer:
    """Тренер для персонализированного обучения"""

    def __init__(self, config):
        self.config = config
        self.device = config.models.device if torch.cuda.is_available() else "cpu"
        self.base_model_name = config.models.base_model

        # Директории
        self.adapters_dir = Path(config.paths.adapters_dir)
        self.style_profiles_dir = Path(config.paths.style_profiles)
        self.adapters_dir.mkdir(parents=True, exist_ok=True)

        # Модели и токенизаторы
        self.tokenizer = None
        self.base_model = None

    def load_my_style_data(self) -> Dict:
        """Загружает данные о моем стиле общения"""
        print("📁 Загрузка ваших данных о стиле общения...")

        style_profile = self.style_profiles_dir / "my_style_profile.json"
        cloned_data = Path(self.config.paths.cloned_data) / "my_communication_style.json"

        my_data = {}

        # Загружаем профиль стиля
        if style_profile.exists():
            with open(style_profile, 'r', encoding='utf-8') as f:
                my_data['style_profile'] = json.load(f)
            print("✅ Профиль стиля загружен")

        # Загружаем клонированные сообщения
        if cloned_data.exists():
            with open(cloned_data, 'r', encoding='utf-8') as f:
                my_data['messages'] = json.load(f)
            print(f"✅ Сообщения загружены: {len(my_data['messages'].get('messages', []))}")

        return my_data

    def prepare_personalized_dataset(self, my_data: Dict) -> pd.DataFrame:
        """Подготавливает персонализированный датасет"""
        print("📊 Подготовка персонализированного датасета...")

        if 'messages' not in my_data or 'messages' not in my_data['messages']:
            print("❌ Нет данных для обучения")
            return pd.DataFrame()

        messages = my_data['messages']['messages']

        data = []

        for msg in messages:
            text = msg.get('text', '')
            context_type = msg.get('context_type', 'unknown')
            context_messages = msg.get('context_messages', [])

            if not text or len(text) < 3:
                continue

            # Форматируем контекст
            if context_messages:
                context = " | ".join(context_messages[-3:])  # Последние 3 сообщения
            else:
                context = f"Контекст: {context_type}"

            # Создаем пример для обучения
            example = {
                'prompt': f"""Стиль общения: {context_type}
Контекст диалога: {context}

Твое сообщение в своем стиле:""",
                'response': text,
                'context_type': context_type,
                'context': context,
                'message_length': len(text.split()),
                'has_emoji': any(emoji in text for emoji in ['😀', '😂', '😊', '😍', '😎'])
            }

            data.append(example)

        df = pd.DataFrame(data)

        print(f"✅ Создано примеров: {len(df)}")
        print(f"📊 Распределение по контекстам:")
        print(df['context_type'].value_counts())

        return df

    def train_context_adapter(self, context_type: str, context_df: pd.DataFrame):
        """Обучает адаптер для конкретного контекста"""
        if context_df.empty or len(context_df) < 10:
            print(f"⚠️  Недостаточно данных для контекста {context_type}")
            return None

        print(f"\n🎯 Обучение адаптера для контекста: {context_type}")
        print(f"📊 Примеров: {len(context_df)}")

        # Создаем датасет
        from datasets import Dataset

        def format_example(row):
            return {
                'text': f"{row['prompt']}\n{row['response']}{self.tokenizer.eos_token}"
            }

        formatted_data = []
        for _, row in context_df.iterrows():
            formatted_data.append(format_example(row))

        dataset_df = pd.DataFrame(formatted_data)
        dataset = Dataset.from_pandas(dataset_df)

        # Токенизируем
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                truncation=True,
                padding="max_length",
                max_length=256
            )

        tokenized_data = dataset.map(tokenize_function, batched=True)

        # Создаем LoRA конфигурацию
        lora_config = LoraConfig(
            r=8,
            lora_alpha=32,
            target_modules=["c_attn", "c_proj"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )

        # Создаем адаптер
        model = get_peft_model(self.base_model, lora_config)
        model.print_trainable_parameters()

        # Аргументы обучения
        training_args = TrainingArguments(
            output_dir=str(self.adapters_dir / f"{context_type}_checkpoints"),
            num_train_epochs=3,
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            warmup_steps=50,
            weight_decay=0.01,
            logging_dir=str(Path(self.config.paths.logs_dir) / context_type),
            logging_steps=10,
            save_strategy="epoch",
            eval_strategy="no",
            report_to="none",
            fp16=self.device == "cuda",
        )

        # Тренер
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_data,
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            ),
        )

        # Обучаем
        print(f"🚀 Начало обучения...")
        trainer.train()

        # Сохраняем адаптер
        adapter_path = self.adapters_dir / f"{context_type}_adapter"
        model.save_pretrained(adapter_path)

        print(f"✅ Адаптер сохранен: {adapter_path}")

        return str(adapter_path)

    def train_general_style_adapter(self, df: pd.DataFrame):
        """Обучает общий адаптер моего стиля"""
        print("\n🎭 Обучение общего адаптера моего стиля...")

        if df.empty or len(df) < 20:
            print("❌ Недостаточно данных для обучения общего стиля")
            return None

        # Создаем датасет
        from datasets import Dataset

        def format_example(row):
            return {
                'text': f"{row['prompt']}\n{row['response']}{self.tokenizer.eos_token}"
            }

        formatted_data = []
        for _, row in df.iterrows():
            formatted_data.append(format_example(row))

        dataset_df = pd.DataFrame(formatted_data)
        dataset = Dataset.from_pandas(dataset_df)

        # Токенизируем
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                truncation=True,
                padding="max_length",
                max_length=256
            )

        tokenized_data = dataset.map(tokenize_function, batched=True)

        # Создаем LoRA конфигурацию
        lora_config = LoraConfig(
            r=16,  # Больший rank для общего стиля
            lora_alpha=64,
            target_modules=["c_attn", "c_proj", "c_fc"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )

        # Создаем адаптер
        model = get_peft_model(self.base_model, lora_config)
        model.print_trainable_parameters()

        # Разделяем на train и validation
        split_dataset = tokenized_data.train_test_split(test_size=0.1, seed=42)

        # Аргументы обучения
        training_args = TrainingArguments(
            output_dir=str(self.adapters_dir / "my_style_checkpoints"),
            num_train_epochs=5,  # Больше эпох для общего стиля
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=str(Path(self.config.paths.logs_dir) / "my_style"),
            logging_steps=10,
            save_strategy="epoch",
            eval_strategy="epoch",
            save_total_limit=2,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            report_to="none",
            fp16=self.device == "cuda",
        )

        # Тренер
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=split_dataset["train"],
            eval_dataset=split_dataset["test"],
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            ),
        )

        # Обучаем
        print(f"🚀 Начало обучения общего стиля...")
        trainer.train()

        # Сохраняем адаптер
        adapter_path = self.adapters_dir / "my_style_adapter"
        model.save_pretrained(adapter_path)

        print(f"✅ Общий адаптер стиля сохранен: {adapter_path}")

        return str(adapter_path)

    def train(self):
        """Запускает полное персонализированное обучение"""
        print("🎯 НАЧАЛО ПЕРСОНАЛИЗИРОВАННОГО ОБУЧЕНИЯ")
        print("=" * 50)

        # Загружаем базовую модель
        self._load_base_model()

        # Загружаем мои данные
        my_data = self.load_my_style_data()

        if not my_data:
            print("❌ Нет данных для обучения")
            return

        # Подготавливаем датасет
        df = self.prepare_personalized_dataset(my_data)

        if df.empty:
            print("❌ Не удалось подготовить датасет")
            return

        # Обучаем адаптеры для каждого контекста
        context_adapters = {}

        for context_type in df['context_type'].unique():
            if context_type == 'unknown':
                continue

            context_df = df[df['context_type'] == context_type]

            if len(context_df) >= self.config.training.personalization.min_messages_per_style:
                adapter_path = self.train_context_adapter(context_type, context_df)
                if adapter_path:
                    context_adapters[context_type] = adapter_path

        # Обучаем общий адаптер моего стиля
        general_adapter = self.train_general_style_adapter(df)

        # Сохраняем информацию об адаптерах
        adapters_info = {
            'base_model': self.base_model_name,
            'general_style_adapter': general_adapter,
            'context_adapters': context_adapters,
            'training_date': pd.Timestamp.now().isoformat(),
            'training_statistics': {
                'total_examples': len(df),
                'context_distribution': df['context_type'].value_counts().to_dict(),
                'average_message_length': df['message_length'].mean(),
                'emoji_frequency': df['has_emoji'].mean()
            }
        }

        info_file = self.adapters_dir / "personalized_adapters_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(adapters_info, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Персонализированное обучение завершено!")
        print(f"📊 Информация сохранена в: {info_file}")
        print(f"🎭 Обучено адаптеров: {len(context_adapters)} контекстов + общий стиль")

        return adapters_info

    def _load_base_model(self):
        """Загружает базовую модель и токенизатор"""
        print(f"🔄 Загрузка базовой модели: {self.base_model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            tie_word_embeddings=False
        )

        print(f"✅ Базовая модель загружена")


def main():
    """Точка входа для персонализированного обучения"""
    import yaml
    from pathlib import Path

    # Загружаем конфигурацию
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("❌ Файл конфигурации не найден")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Запускаем обучение
    print("🚀 Запуск персонализированного обучения...")

    try:
        trainer = PersonalizedStyleTrainer(config_dict)
        trainer.train()
    except KeyboardInterrupt:
        print("\n👋 Обучение прервано")
    except Exception as e:
        print(f"❌ Ошибка обучения: {e}")


if __name__ == "__main__":
    main()