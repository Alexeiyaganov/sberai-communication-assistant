#!/usr/bin/env python3
"""
Маршрутизатор для выбора подходящего контекста общения
"""

from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass


@dataclass
class ContextRoute:
    """Маршрут для контекста общения"""
    primary_context: str
    secondary_contexts: List[str]
    confidence: float
    reasoning: str
    suggestions: Dict


class ContextRouter:
    """Маршрутизатор контекстов общения"""

    def __init__(self, config):
        self.config = config
        self.contexts = config.communication_contexts

        # Веса для разных факторов
        self.weights = {
            'keyword_match': 0.4,
            'dialog_history': 0.3,
            'time_of_day': 0.1,
            'user_preferences': 0.2
        }

        # Время суток и контексты
        self.time_contexts = {
            'morning': ['professional', 'friendly'],
            'afternoon': ['professional', 'friendly'],
            'evening': ['family', 'romantic', 'friendly'],
            'night': ['romantic', 'creative', 'friendly']
        }

        # Правила для контекстов
        self.context_rules = self._build_context_rules()

    def _build_context_rules(self) -> Dict:
        """Строит правила для определения контекстов"""
        return {
            'professional': {
                'keywords': ['работа', 'проект', 'задача', 'встреча', 'коллега',
                             'начальник', 'дедлайн', 'отчет', 'презентация', 'бизнес'],
                'avoid_keywords': ['люблю', 'обнимаю', 'целую', 'ха-ха'],
                'time_preference': ['morning', 'afternoon'],
                'typical_length': 'medium',
                'emoji_limit': 1
            },
            'family': {
                'keywords': ['мама', 'папа', 'родители', 'брат', 'сестра',
                             'семья', 'родные', 'дети', 'внуки', 'бабушка', 'дедушка'],
                'avoid_keywords': ['уважаемый', 'коллега', 'протокол'],
                'time_preference': ['evening', 'weekend'],
                'typical_length': 'short',
                'emoji_limit': 3
            },
            'romantic': {
                'keywords': ['люблю', 'обожаю', 'дорогой', 'милый', 'любимый',
                             'романтика', 'отношения', 'чувства', 'сердце', 'поцелуй'],
                'emojis': ['❤️', '💕', '😘', '💋', '😍', '🥰'],
                'time_preference': ['evening', 'night'],
                'typical_length': 'medium',
                'emoji_limit': 2
            },
            'friendly': {
                'keywords': ['друг', 'подруга', 'приятель', 'тусовка', 'встреча',
                             'кафе', 'кино', 'прогулка', 'вечеринка'],
                'emojis': ['😊', '😂', '😎', '👍', '👋'],
                'time_preference': ['afternoon', 'evening'],
                'typical_length': 'short',
                'emoji_limit': 3
            },
            'creative': {
                'keywords': ['идея', 'творчество', 'вдохновение', 'проект', 'искусство',
                             'музыка', 'рисунок', 'писать', 'создавать', 'креатив'],
                'time_preference': ['night', 'flexible'],
                'typical_length': 'long',
                'emoji_limit': 2
            }
        }

    def route_context(self,
                      message: str,
                      dialog_history: List[str] = None,
                      user_preferences: Dict = None,
                      time_info: Dict = None) -> ContextRoute:
        """Определяет подходящий контекст для ответа"""

        # Анализируем текущее сообщение
        message_analysis = self._analyze_message(message)

        # Анализируем историю диалога
        history_analysis = self._analyze_history(dialog_history) if dialog_history else {}

        # Учитываем время
        time_analysis = self._analyze_time(time_info) if time_info else {}

        # Учитываем предпочтения пользователя
        preferences_analysis = self._analyze_preferences(user_preferences) if user_preferences else {}

        # Собираем все факторы
        all_factors = {
            'message': message_analysis,
            'history': history_analysis,
            'time': time_analysis,
            'preferences': preferences_analysis
        }

        # Вычисляем scores для каждого контекста
        context_scores = {}

        for context_name, rules in self.context_rules.items():
            score = 0.0

            # Ключевые слова в сообщении
            keyword_score = self._calculate_keyword_score(message, rules['keywords'])
            score += keyword_score * self.weights['keyword_match']

            # История диалога
            if 'recent_context' in history_analysis:
                if history_analysis['recent_context'] == context_name:
                    score += 0.3 * self.weights['dialog_history']

            # Время суток
            if 'current_period' in time_analysis:
                if time_analysis['current_period'] in rules.get('time_preference', []):
                    score += 0.2 * self.weights['time_of_day']

            # Предпочтения пользователя
            if 'fav_contexts' in preferences_analysis:
                if context_name in preferences_analysis['fav_contexts']:
                    score += 0.3 * self.weights['user_preferences']

            # Избегаем конфликтующих ключевых слов
            avoid_score = self._calculate_avoid_score(message, rules.get('avoid_keywords', []))
            score -= avoid_score * 0.2

            context_scores[context_name] = score

        # Выбираем лучший контекст
        sorted_contexts = sorted(context_scores.items(), key=lambda x: x[1], reverse=True)

        if not sorted_contexts:
            primary_context = 'friendly'  # По умолчанию
            confidence = 0.5
        else:
            primary_context, primary_score = sorted_contexts[0]

            # Нормализуем confidence
            max_possible_score = sum(self.weights.values())
            confidence = min(primary_score / max_possible_score, 1.0)

        # Вторичные контексты (если scores близки)
        secondary_contexts = []
        if len(sorted_contexts) > 1:
            second_context, second_score = sorted_contexts[1]
            if abs(primary_score - second_score) < 0.1:  # Близкие scores
                secondary_contexts.append(second_context)

        # Формируем рекомендации
        suggestions = self._generate_suggestions(
            primary_context,
            message_analysis,
            all_factors
        )

        # Формируем reasoning
        reasoning_parts = []

        if message_analysis.get('has_context_keywords'):
            reasoning_parts.append("Обнаружены ключевые слова контекста")

        if history_analysis.get('recent_context') == primary_context:
            reasoning_parts.append("Совпадает с недавним контекстом диалога")

        if time_analysis.get('current_period') in self.context_rules[primary_context].get('time_preference', []):
            reasoning_parts.append("Подходит для текущего времени суток")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Определено по общим признакам"

        return ContextRoute(
            primary_context=primary_context,
            secondary_contexts=secondary_contexts,
            confidence=confidence,
            reasoning=reasoning,
            suggestions=suggestions
        )

    def _analyze_message(self, message: str) -> Dict:
        """Анализирует текущее сообщение"""
        if not message:
            return {}

        text_lower = message.lower()

        analysis = {
            'length': len(message.split()),
            'has_questions': '?' in message,
            'has_exclamations': '!' in message,
            'emoji_count': self._count_emojis(message),
            'has_context_keywords': False
        }

        # Проверяем наличие ключевых слов для всех контекстов
        for context_name, rules in self.context_rules.items():
            for keyword in rules['keywords']:
                if keyword in text_lower:
                    analysis['has_context_keywords'] = True
                    analysis['detected_keyword'] = keyword
                    analysis['detected_context'] = context_name
                    break
            if analysis.get('has_context_keywords'):
                break

        return analysis

    def _analyze_history(self, history: List[str]) -> Dict:
        """Анализирует историю диалога"""
        if not history:
            return {}

        # Берем последние 5 сообщений
        recent_messages = history[-5:] if len(history) > 5 else history

        # Пытаемся определить контекст из истории
        recent_contexts = []

        for msg in recent_messages:
            for context_name, rules in self.context_rules.items():
                for keyword in rules['keywords']:
                    if keyword in msg.lower():
                        recent_contexts.append(context_name)
                        break

        # Самый частый контекст в истории
        from collections import Counter
        if recent_contexts:
            context_counts = Counter(recent_contexts)
            most_common = context_counts.most_common(1)[0]
            return {
                'recent_context': most_common[0],
                'context_frequency': most_common[1] / len(recent_messages)
            }

        return {}

    def _analyze_time(self, time_info: Dict) -> Dict:
        """Анализирует временные факторы"""
        # time_info может содержать: hour, weekday, is_holiday и т.д.

        if 'hour' not in time_info:
            return {}

        hour = time_info['hour']

        # Определяем период суток
        if 6 <= hour < 12:
            period = 'morning'
        elif 12 <= hour < 18:
            period = 'afternoon'
        elif 18 <= hour < 23:
            period = 'evening'
        else:
            period = 'night'

        analysis = {
            'current_period': period,
            'hour': hour
        }

        # Учитываем день недели
        if 'weekday' in time_info:
            weekday = time_info['weekday']
            analysis['weekday'] = weekday

            if weekday >= 5:  # Суббота или воскресенье
                analysis['is_weekend'] = True
                # В выходные больше семейного и дружеского общения
                analysis['period_adjustment'] = 'more_casual'

        # Учитываем праздники
        if 'is_holiday' in time_info and time_info['is_holiday']:
            analysis['is_holiday'] = True
            analysis['period_adjustment'] = 'festive'

        return analysis

    def _analyze_preferences(self, preferences: Dict) -> Dict:
        """Анализирует предпочтения пользователя"""
        analysis = {}

        if 'fav_contexts' in preferences:
            analysis['fav_contexts'] = preferences['fav_contexts']

        if 'avoid_contexts' in preferences:
            analysis['avoid_contexts'] = preferences['avoid_contexts']

        if 'communication_style' in preferences:
            analysis['style'] = preferences['communication_style']

        return analysis

    def _calculate_keyword_score(self, message: str, keywords: List[str]) -> float:
        """Вычисляет score по ключевым словам"""
        if not message or not keywords:
            return 0.0

        text_lower = message.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)

        # Нормализуем score
        return min(matches * 0.3, 1.0)

    def _calculate_avoid_score(self, message: str, avoid_words: List[str]) -> float:
        """Вычисляет score по избегаемым словам"""
        if not message or not avoid_words:
            return 0.0

        text_lower = message.lower()
        matches = sum(1 for word in avoid_words if word in text_lower)

        return min(matches * 0.2, 1.0)

    def _count_emojis(self, text: str) -> int:
        """Считает количество эмодзи в тексте"""
        import re

        # Паттерн для эмодзи
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        )

        return len(emoji_pattern.findall(text))

    def _generate_suggestions(self, context: str, message_analysis: Dict,
                              all_factors: Dict) -> Dict:
        """Генерирует рекомендации для выбранного контекста"""
        rules = self.context_rules.get(context, {})

        suggestions = {
            'tone': self._suggest_tone(context, message_analysis),
            'length': rules.get('typical_length', 'medium'),
            'emoji_limit': rules.get('emoji_limit', 2),
            'key_phrases': self._suggest_key_phrases(context),
            'avoid': rules.get('avoid_keywords', [])[:3]
        }

        # Адаптируем под анализ сообщения
        if message_analysis.get('has_questions'):
            suggestions['response_type'] = 'answer'
        elif message_analysis.get('has_exclamations'):
            suggestions['response_type'] = 'reaction'

        # Учитываем время
        if 'time' in all_factors and 'current_period' in all_factors['time']:
            period = all_factors['time']['current_period']
            if period == 'night' and context != 'professional':
                suggestions['tone'] = 'more_relaxed'

        return suggestions

    def _suggest_tone(self, context: str, message_analysis: Dict) -> str:
        """Предлагает тон для ответа"""
        tones = {
            'professional': 'formal_respectful',
            'family': 'warm_caring',
            'romantic': 'tender_affectionate',
            'friendly': 'casual_friendly',
            'creative': 'expressive_inspirational'
        }

        base_tone = tones.get(context, 'neutral')

        # Адаптируем под сообщение
        if message_analysis.get('has_exclamations'):
            if context in ['friendly', 'creative']:
                return 'enthusiastic_' + base_tone

        return base_tone

    def _suggest_key_phrases(self, context: str) -> List[str]:
        """Предлагает ключевые фразы для контекста"""
        phrases = {
            'professional': [
                "Благодарю за сообщение",
                "Предлагаю рассмотреть",
                "Согласовано",
                "Прошу уточнить"
            ],
            'family': [
                "Привет, как дела?",
                "Обнимаю крепко",
                "Целую",
                "Скучаю по вам"
            ],
            'romantic': [
                "Привет, мой дорогой",
                "Скучаю по тебе",
                "Люблю тебя",
                "Ты у меня самый лучший"
            ],
            'friendly': [
                "Привет!",
                "Как дела?",
                "Что нового?",
                "Давай встретимся"
            ],
            'creative': [
                "Интересная мысль!",
                "Вдохновляюще",
                "Креативный подход",
                "Продолжаем творить"
            ]
        }

        return phrases.get(context, ["Привет!", "Как дела?"])

    def suggest_multiple_contexts(self, message: str, num_suggestions: int = 3) -> List[Dict]:
        """Предлагает несколько возможных контекстов"""
        if not message:
            return []

        text_lower = message.lower()
        suggestions = []

        for context_name, rules in self.context_rules.items():
            score = 0.0
            matched_keywords = []

            # Проверяем ключевые слова
            for keyword in rules['keywords']:
                if keyword in text_lower:
                    score += 0.3
                    matched_keywords.append(keyword)

            # Проверяем эмодзи
            if 'emojis' in rules:
                for emoji in rules['emojis']:
                    if emoji in message:
                        score += 0.2

            if score > 0:
                suggestions.append({
                    'context': context_name,
                    'score': score,
                    'matched_keywords': matched_keywords[:3],
                    'description': self._get_context_description(context_name)
                })

        # Сортируем по score
        suggestions.sort(key=lambda x: x['score'], reverse=True)

        return suggestions[:num_suggestions]

    def _get_context_description(self, context: str) -> str:
        """Возвращает описание контекста"""
        descriptions = {
            'professional': "Деловое, формальное общение",
            'family': "Семейное, неформальное общение",
            'romantic': "Романтическое общение",
            'friendly': "Дружеское общение",
            'creative': "Креативное, творческое общение"
        }

        return descriptions.get(context, "Общее общение")

    def validate_context_switch(self, current_context: str,
                                proposed_context: str,
                                dialog_history: List[str]) -> Tuple[bool, str]:
        """Проверяет, можно ли переключать контекст"""

        # Не переключаемся на тот же контекст
        if current_context == proposed_context:
            return True, "Тот же контекст"

        # Определяем совместимость контекстов
        compatibility = {
            'professional': ['friendly', 'creative'],
            'family': ['friendly', 'romantic'],
            'romantic': ['family', 'friendly'],
            'friendly': ['professional', 'family', 'romantic', 'creative'],
            'creative': ['professional', 'friendly']
        }

        if proposed_context not in compatibility.get(current_context, []):
            return False, f"Резкий переход с {current_context} на {proposed_context}"

        # Проверяем историю
        if dialog_history and len(dialog_history) > 3:
            recent_contexts = []
            for msg in dialog_history[-3:]:
                for ctx in self.context_rules.keys():
                    for keyword in self.context_rules[ctx]['keywords']:
                        if keyword in msg.lower():
                            recent_contexts.append(ctx)
                            break

            # Если в истории уже был предложенный контекст, переход более плавный
            if proposed_context in recent_contexts:
                return True, "Плавный переход на основе истории"

        return True, "Переход разрешен"