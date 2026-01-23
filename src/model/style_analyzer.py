#!/usr/bin/env python3
"""
Анализатор стилей общения для разных контекстов
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class CommunicationStyle:
    """Стиль общения"""
    context: str  # professional, family, romantic, friendly, creative
    formality: float  # 0.0-1.0
    emotionality: float  # 0.0-1.0
    humor_level: float  # 0.0-1.0
    emoji_frequency: float  # 0.0-1.0
    typical_length: str  # short, medium, long
    common_phrases: List[str]
    avoid_phrases: List[str]


class CommunicationStyleAnalyzer:
    """Анализатор стилей общения"""

    def __init__(self, config):
        self.config = config
        self.contexts = config.communication_contexts

        # Шаблоны для разных контекстов
        self.context_patterns = self._load_context_patterns()

        # Стоп-слова для русского языка
        self.stop_words = {
            'это', 'как', 'так', 'и', 'в', 'над', 'к', 'до', 'не', 'на',
            'но', 'за', 'то', 'с', 'ли', 'а', 'во', 'от', 'со', 'для', 'о'
        }

    def _load_context_patterns(self) -> Dict:
        """Загружает паттерны для разных контекстов"""
        return {
            'professional': {
                'formality_words': ['уважаемый', 'коллега', 'прошу', 'предлагаю', 'согласовано'],
                'emotional_words': [],
                'humor_words': [],
                'typical_length': 'medium',
                'common_endings': ['С уважением', 'Благодарю', 'С наилучшими пожеланиями']
            },
            'family': {
                'formality_words': [],
                'emotional_words': ['люблю', 'обнимаю', 'целую', 'скучаю'],
                'humor_words': ['ха-ха', 'смешно', 'прикол'],
                'typical_length': 'short',
                'common_endings': ['Целую', 'Обнимаю', 'Люблю']
            },
            'romantic': {
                'formality_words': [],
                'emotional_words': ['люблю', 'обожаю', 'нежный', 'романтик', 'мечта'],
                'humor_words': [],
                'typical_length': 'medium',
                'common_endings': ['Целую', 'Обнимаю', 'Твой/Твоя']
            },
            'friendly': {
                'formality_words': [],
                'emotional_words': ['класс', 'отлично', 'супер', 'круто'],
                'humor_words': ['лол', 'кек', 'ржака', 'прикол'],
                'typical_length': 'short',
                'common_endings': ['Пока', 'До связи', 'Удачи']
            },
            'creative': {
                'formality_words': [],
                'emotional_words': ['вдохновение', 'креатив', 'творчество'],
                'humor_words': ['ирония', 'сарказм', 'шутка'],
                'typical_length': 'long',
                'common_endings': ['Творческих успехов', 'Вдохновения']
            }
        }

    def analyze_context(self, text: str, dialog_context: str = None) -> Dict:
        """Анализирует контекст общения"""
        if not text:
            return {
                'detected_context': 'unknown',
                'confidence': 0.0,
                'suggested_contexts': []
            }

        text_lower = text.lower()

        # Если указан контекст диалога, используем его как приоритет
        if dialog_context and dialog_context in self.context_patterns:
            primary_context = dialog_context
        else:
            # Определяем контекст автоматически
            context_scores = {}

            for context, patterns in self.context_patterns.items():
                score = 0.0

                # Проверяем формальные слова
                for word in patterns['formality_words']:
                    if word in text_lower:
                        score += 0.3

                # Проверяем эмоциональные слова
                for word in patterns['emotional_words']:
                    if word in text_lower:
                        score += 0.2

                # Проверяем юмор
                for word in patterns['humor_words']:
                    if word in text_lower:
                        score += 0.2

                context_scores[context] = score

            # Выбираем контекст с наибольшим score
            if context_scores:
                primary_context = max(context_scores.items(), key=lambda x: x[1])[0]
            else:
                primary_context = 'friendly'  # По умолчанию дружеский

        # Дополнительные проверки
        if self._is_work_related(text):
            primary_context = 'professional'
        elif self._is_family_related(text):
            primary_context = 'family'
        elif self._is_romantic_related(text):
            primary_context = 'romantic'

        # Собираем характеристики
        characteristics = {
            'formality': self._calculate_formality(text),
            'emotionality': self._calculate_emotionality(text),
            'humor_level': self._calculate_humor_level(text),
            'emoji_frequency': self._calculate_emoji_frequency(text),
            'message_length': self._classify_length(text),
            'contains_questions': '?' in text,
            'contains_exclamations': '!' in text,
            'word_count': len(text.split())
        }

        return {
            'detected_context': primary_context,
            'confidence': 0.8,  # Можно сделать более точную оценку
            'characteristics': characteristics,
            'suggested_responses': self._suggest_response_style(primary_context, characteristics)
        }

    def _is_work_related(self, text: str) -> bool:
        """Проверяет, относится ли текст к работе"""
        work_keywords = ['работа', 'проект', 'задача', 'встреча', 'коллега',
                         'начальник', 'дедлайн', 'отчет', 'презентация']
        return any(keyword in text.lower() for keyword in work_keywords)

    def _is_family_related(self, text: str) -> bool:
        """Проверяет, относится ли текст к семье"""
        family_keywords = ['мама', 'папа', 'родители', 'брат', 'сестра',
                           'семья', 'родные', 'дети', 'внуки']
        return any(keyword in text.lower() for keyword in family_keywords)

    def _is_romantic_related(self, text: str) -> bool:
        """Проверяет, относится ли текст к романтике"""
        romantic_keywords = ['люблю', 'обожаю', 'дорогой', 'милый', 'любимый',
                             'романтика', 'отношения', 'чувства', 'сердце']
        romantic_emojis = ['❤️', '💕', '😘', '💋', '😍']

        has_keywords = any(keyword in text.lower() for keyword in romantic_keywords)
        has_emojis = any(emoji in text for emoji in romantic_emojis)

        return has_keywords or has_emojis

    def _calculate_formality(self, text: str) -> float:
        """Вычисляет уровень формальности"""
        formal_words = ['уважаемый', 'прошу', 'предлагаю', 'согласовано', 'документ',
                        'договор', 'сотрудничество', 'официально']

        words = text.lower().split()
        if not words:
            return 0.0

        formal_count = sum(1 for word in words if word in formal_words)
        return min(formal_count / len(words) * 3, 1.0)

    def _calculate_emotionality(self, text: str) -> float:
        """Вычисляет уровень эмоциональности"""
        emotional_words = ['люблю', 'обожаю', 'ненавижу', 'злюсь', 'радуюсь',
                           'грущу', 'волнуюсь', 'беспокоюсь', 'восхищаюсь']
        emotional_emojis = ['❤️', '😍', '😢', '😂', '😡', '🥰', '😭']

        score = 0.0

        # Эмоциональные слова
        words = text.lower().split()
        if words:
            emotional_word_count = sum(1 for word in words if word in emotional_words)
            score += emotional_word_count / len(words) * 2

        # Эмоциональные эмодзи
        emoji_count = sum(1 for emoji in emotional_emojis if emoji in text)
        score += emoji_count * 0.1

        # Восклицательные знаки
        exclamation_count = text.count('!')
        score += min(exclamation_count * 0.05, 0.3)

        return min(score, 1.0)

    def _calculate_humor_level(self, text: str) -> float:
        """Вычисляет уровень юмора"""
        humor_indicators = ['ха-ха', 'хе-хе', 'лол', 'кек', 'смешно', 'прикол',
                            'шутка', 'юмор', 'анекдот', '😂', '🤣', '😄']

        score = 0.0

        for indicator in humor_indicators:
            if indicator in text.lower():
                score += 0.2

        return min(score, 1.0)

    def _calculate_emoji_frequency(self, text: str) -> float:
        """Вычисляет частоту использования эмодзи"""
        # Простой паттерн для эмодзи
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        )

        emojis = emoji_pattern.findall(text)

        if not text:
            return 0.0

        return min(len(emojis) / len(text) * 100, 1.0)

    def _classify_length(self, text: str) -> str:
        """Классифицирует длину сообщения"""
        word_count = len(text.split())

        if word_count < 5:
            return 'short'
        elif word_count < 20:
            return 'medium'
        else:
            return 'long'

    def _suggest_response_style(self, context: str, characteristics: Dict) -> Dict:
        """Предлагает стиль для ответа"""
        suggestions = {
            'professional': {
                'tone': 'formal',
                'emoji_limit': 0,
                'length': 'medium',
                'key_phrases': ['Благодарю', 'Согласовано', 'Предлагаю', 'Прошу рассмотреть']
            },
            'family': {
                'tone': 'warm',
                'emoji_limit': 3,
                'length': 'short',
                'key_phrases': ['Целую', 'Обнимаю', 'Люблю', 'Скучаю']
            },
            'romantic': {
                'tone': 'tender',
                'emoji_limit': 2,
                'length': 'medium',
                'key_phrases': ['Милый', 'Дорогой', 'Люблю', 'Скучаю по тебе']
            },
            'friendly': {
                'tone': 'casual',
                'emoji_limit': 3,
                'length': 'short',
                'key_phrases': ['Привет', 'Как дела', 'Что нового', 'Давай созвонимся']
            },
            'creative': {
                'tone': 'expressive',
                'emoji_limit': 2,
                'length': 'long',
                'key_phrases': ['Интересно', 'Креативно', 'Вдохновляюще', 'Творчески']
            }
        }

        base_suggestion = suggestions.get(context, suggestions['friendly'])

        # Адаптируем под характеристики
        adapted = base_suggestion.copy()

        if characteristics['emotionality'] > 0.7:
            adapted['tone'] = 'emotional'
        elif characteristics['formality'] > 0.7:
            adapted['tone'] = 'very_formal'

        if characteristics['emoji_frequency'] > 0.5:
            adapted['emoji_limit'] = min(adapted['emoji_limit'] + 2, 5)

        return adapted

    def extract_style_signature(self, messages: List[str], context: str) -> Dict:
        """Извлекает сигнатуру стиля из набора сообщений"""
        if not messages:
            return {}

        # Анализируем все сообщения
        all_characteristics = []

        for msg in messages:
            analysis = self.analyze_context(msg, context)
            all_characteristics.append(analysis['characteristics'])

        # Вычисляем средние значения
        avg_characteristics = {}
        if all_characteristics:
            for key in all_characteristics[0].keys():
                if isinstance(all_characteristics[0][key], (int, float)):
                    values = [ch[key] for ch in all_characteristics if isinstance(ch[key], (int, float))]
                    if values:
                        avg_characteristics[key] = np.mean(values)

        # Самые частые слова
        common_words = self._extract_common_words(messages)

        # Частые фразы
        common_phrases = self._extract_common_phrases(messages)

        return {
            'context': context,
            'avg_characteristics': avg_characteristics,
            'common_words': common_words[:10],
            'common_phrases': common_phrases[:5],
            'message_count': len(messages),
            'style_description': self._describe_style(avg_characteristics)
        }

    def _extract_common_words(self, messages: List[str]) -> List[str]:
        """Извлекает общие слова из сообщений"""
        all_words = []

        for msg in messages:
            words = re.findall(r'\b[а-яё]{3,}\b', msg.lower())
            filtered_words = [word for word in words if word not in self.stop_words]
            all_words.extend(filtered_words)

        # Считаем частоту
        from collections import Counter
        word_counts = Counter(all_words)

        return [word for word, count in word_counts.most_common(20)]

    def _extract_common_phrases(self, messages: List[str]) -> List[str]:
        """Извлекает общие фразы из сообщений"""
        # Простая реализация - ищем повторяющиеся последовательности из 2-3 слов
        phrases = []

        for msg in messages:
            words = msg.lower().split()
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i + 2])
                if len(phrase) > 5 and phrase not in self.stop_words:
                    phrases.append(phrase)

        # Считаем частоту
        from collections import Counter
        phrase_counts = Counter(phrases)

        return [phrase for phrase, count in phrase_counts.most_common(10) if count > 1]

    def _describe_style(self, characteristics: Dict) -> str:
        """Описание стиля на основе характеристик"""
        if not characteristics:
            return "Неизвестный стиль"

        descriptions = []

        # Формальность
        formality = characteristics.get('formality', 0)
        if formality > 0.7:
            descriptions.append("формальный")
        elif formality > 0.3:
            descriptions.append("умеренно формальный")
        else:
            descriptions.append("неформальный")

        # Эмоциональность
        emotionality = characteristics.get('emotionality', 0)
        if emotionality > 0.7:
            descriptions.append("эмоциональный")
        elif emotionality > 0.3:
            descriptions.append("умеренно эмоциональный")
        else:
            descriptions.append("сдержанный")

        # Длина сообщений
        avg_length = characteristics.get('word_count', 0)
        if avg_length > 15:
            descriptions.append("развернутый")
        elif avg_length > 5:
            descriptions.append("умеренный по длине")
        else:
            descriptions.append("лаконичный")

        return ', '.join(descriptions)