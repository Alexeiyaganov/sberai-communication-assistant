import os
import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import textwrap
import gradio as gr


class AutoProjectAnalyzer:
    def __init__(self, project_path="/content/sberai-communication-assistant"):
        """Инициализация анализатора для указанного пути"""
        self.project_path = Path(project_path)

        # Создаем папку если не существует
        if not self.project_path.exists():
            self.project_path.mkdir(parents=True)
            print(f"📁 Создана папка проекта: {self.project_path}")
        else:
            print(f"✅ Папка проекта найдена: {self.project_path}")

        # Инициализируем анализаторы
        self._setup_analyzers()

    def _setup_analyzers(self):
        """Настройка встроенных анализаторов кода"""
        self.analyzers = {
            'structure': self.analyze_structure,
            'imports': self.analyze_imports,
            'errors': self.find_potential_errors,
            'security': self.check_security_issues,
            'performance': self.check_performance_issues,
            'best_practices': self.check_best_practices
        }

    def get_project_summary(self):
        """Получить сводку о проекте"""
        try:
            py_files = list(self.project_path.rglob("*.py"))
            total_lines = 0
            total_size = 0

            for file in py_files[:20]:  # Ограничиваем для скорости
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                        total_size += file.stat().st_size
                except:
                    continue

            return {
                'total_py_files': len(py_files),
                'total_lines': total_lines,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'main_files': [str(f.relative_to(self.project_path)) for f in py_files[:10]]
            }
        except Exception as e:
            return {'error': str(e)}

    def analyze_structure(self):
        """Анализ структуры проекта"""
        structure = {
            'files_by_type': {},
            'directory_tree': [],
            'entry_points': []
        }

        # Анализ по типам файлов
        for ext in ['.py', '.pyx', '.ipynb', '.txt', '.md', '.yaml', '.yml', '.json']:
            files = list(self.project_path.rglob(f"*{ext}"))
            structure['files_by_type'][ext] = len(files)

        # Построение дерева директорий (упрощенное)
        def build_tree(path, prefix=""):
            try:
                items = list(path.iterdir())
                for i, item in enumerate(sorted(items)):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "

                    if item.is_file():
                        structure['directory_tree'].append(f"{prefix}{connector}{item.name}")
                    elif item.is_dir():
                        structure['directory_tree'].append(f"{prefix}{connector}{item.name}/")
                        extension = "    " if is_last else "│   "
                        build_tree(item, prefix + extension)
            except:
                pass

        build_tree(self.project_path)

        # Поиск точек входа
        entry_patterns = ['main.py', 'app.py', 'run.py', 'setup.py', '__main__.py']
        for pattern in entry_patterns:
            for file in self.project_path.rglob(pattern):
                structure['entry_points'].append(str(file.relative_to(self.project_path)))

        return structure

    def analyze_imports(self):
        """Анализ импортов проекта"""
        imports_info = {
            'external_imports': set(),
            'internal_imports': set(),
            'import_errors': [],
            'circular_deps': []
        }

        try:
            for py_file in self.project_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Парсинг AST для анализа импортов
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports_info['external_imports'].add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports_info['external_imports'].add(node.module.split('.')[0])
                except SyntaxError as e:
                    imports_info['import_errors'].append({
                        'file': str(py_file.relative_to(self.project_path)),
                        'error': str(e)
                    })
                except:
                    continue

        except Exception as e:
            imports_info['error'] = str(e)

        return imports_info

    def find_potential_errors(self):
        """Поиск потенциальных ошибок в коде"""
        errors = []

        try:
            # Используем pyflakes для статического анализа
            for py_file in self.project_path.rglob("*.py"):
                try:
                    result = subprocess.run(
                        ['python', '-m', 'pyflakes', str(py_file)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.stdout:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if line:
                                errors.append({
                                    'file': str(py_file.relative_to(self.project_path)),
                                    'issue': line
                                })
                except:
                    continue

            # Дополнительная проверка через ast
            for py_file in self.project_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Проверка на try-except без указания исключения
                    if 'except:' in content and 'except Exception:' not in content:
                        errors.append({
                            'file': str(py_file.relative_to(self.project_path)),
                            'issue': 'Используется голый except (bare except) - укажите конкретные исключения'
                        })

                    # Проверка на print для отладки
                    if 'print(' in content and 'DEBUG' not in str(py_file):
                        errors.append({
                            'file': str(py_file.relative_to(self.project_path)),
                            'issue': 'Обнаружен print() - возможно, стоит использовать логирование'
                        })

                except:
                    continue

        except Exception as e:
            errors.append({'error': f'Ошибка анализа: {str(e)}'})

        return errors

    def check_security_issues(self):
        """Проверка на проблемы безопасности"""
        security_issues = []

        dangerous_patterns = [
            ('eval(', 'Использование eval() может быть опасно'),
            ('exec(', 'Использование exec() может быть опасно'),
            ('pickle.loads(', 'Десериализация pickle может быть уязвима'),
            ('subprocess.call(', 'Проверьте аргументы subprocess'),
            ('os.system(', 'Использование os.system() может быть уязвимо'),
            ('input()', 'Непроверенный пользовательский ввод'),
            ('getpass', 'Проверьте обработку паролей'),
            ('open(', 'Проверьте режимы открытия файлов'),
        ]

        for py_file in self.project_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern, message in dangerous_patterns:
                    if pattern in content:
                        security_issues.append({
                            'file': str(py_file.relative_to(self.project_path)),
                            'pattern': pattern,
                            'message': message
                        })
            except:
                continue

        return security_issues

    def check_performance_issues(self):
        """Проверка на проблемы производительности"""
        performance_issues = []

        anti_patterns = [
            ('for item in list:', 'Итерация по списку с индексами может быть медленнее'),
            ('list.append() в цикле', 'Рассмотрите list comprehension'),
            ('deepcopy', 'Глубокое копирование может быть медленным'),
            ('sleep(', 'Блокирующие вызовы могут замедлить работу'),
            ('time.sleep(', 'Рассмотрите асинхронные альтернативы'),
            ('globals()', 'Использование globals() замедляет доступ'),
        ]

        for py_file in self.project_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.lower()

                # Проверка антипаттернов
                if 'for ' in lines and 'range(len(' in lines:
                    performance_issues.append({
                        'file': str(py_file.relative_to(self.project_path)),
                        'issue': 'Использование range(len(list)) вместо enumerate()',
                        'suggestion': 'Используйте for i, item in enumerate(items):'
                    })

                if '.append(' in lines and ('for ' in lines or 'while ' in lines):
                    performance_issues.append({
                        'file': str(py_file.relative_to(self.project_path)),
                        'issue': 'list.append() внутри цикла',
                        'suggestion': 'Рассмотрите list comprehension или предварительное выделение памяти'
                    })

            except:
                continue

        return performance_issues

    def check_best_practices(self):
        """Проверка соблюдения best practices"""
        best_practices = {
            'violations': [],
            'suggestions': []
        }

        for py_file in self.project_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Проверка на docstrings
                if 'def ' in content and '"""' not in content and "'''" not in content:
                    best_practices['violations'].append({
                        'file': str(py_file.relative_to(self.project_path)),
                        'issue': 'Отсутствуют docstrings у функций/классов'
                    })

                # Проверка на type hints
                if 'def ' in content and '->' not in content and '# type:' not in content:
                    best_practices['suggestions'].append({
                        'file': str(py_file.relative_to(self.project_path)),
                        'suggestion': 'Добавьте type hints для лучшей читаемости'
                    })

                # Проверка на магические числа
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if any(char.isdigit() for char in line) and not any(
                            keyword in line for keyword in ['import', 'def', 'class', '#']):
                        # Упрощенная проверка на магические числа
                        if ' = ' in line and any(str(num) in line for num in [0, 1, 2, 10, 100, 1000]):
                            best_practices['suggestions'].append({
                                'file': f"{str(py_file.relative_to(self.project_path))}:{i + 1}",
                                'suggestion': 'Рассмотрите использование констант вместо магических чисел'
                            })

            except:
                continue

        return best_practices

    def run_full_analysis(self):
        """Запуск полного анализа проекта"""
        analysis_results = {}

        print("🔍 Запускаю анализ проекта...")

        for name, analyzer in self.analyzers.items():
            try:
                print(f"  ⏳ Анализирую {name}...")
                analysis_results[name] = analyzer()
            except Exception as e:
                analysis_results[name] = {'error': str(e)}

        print("✅ Анализ завершен!")
        return analysis_results

    def generate_report(self, analysis_results):
        """Генерация читаемого отчета"""
        report = []

        # Сводка проекта
        summary = self.get_project_summary()
        report.append("📊 СВОДКА ПРОЕКТА")
        report.append("=" * 50)
        report.append(f"📁 Папка проекта: {self.project_path}")
        report.append(f"📄 Файлов .py: {summary.get('total_py_files', 0)}")
        report.append(f"📝 Строк кода: {summary.get('total_lines', 0)}")
        report.append(f"💾 Размер: {summary.get('total_size_mb', 0)} MB")

        if 'main_files' in summary:
            report.append("\nОсновные файлы:")
            for file in summary['main_files'][:5]:
                report.append(f"  • {file}")

        # Анализ структуры
        if 'structure' in analysis_results:
            structure = analysis_results['structure']
            report.append("\n🏗️ СТРУКТУРА ПРОЕКТА")
            report.append("=" * 50)

            if 'files_by_type' in structure:
                report.append("Файлы по типам:")
                for ext, count in structure['files_by_type'].items():
                    if count > 0:
                        report.append(f"  {ext}: {count}")

            if 'entry_points' in structure and structure['entry_points']:
                report.append("\n🚀 Точки входа:")
                for entry in structure['entry_points']:
                    report.append(f"  • {entry}")

        # Потенциальные ошибки
        if 'errors' in analysis_results and analysis_results['errors']:
            report.append("\n❌ ПОТЕНЦИАЛЬНЫЕ ОШИБКИ")
            report.append("=" * 50)
            for error in analysis_results['errors'][:10]:  # Ограничиваем вывод
                if 'file' in error:
                    report.append(f"📄 {error['file']}")
                    report.append(f"   ⚠️  {error.get('issue', 'Неизвестная проблема')}")

        # Проблемы безопасности
        if 'security' in analysis_results and analysis_results['security']:
            report.append("\n🔒 ПРОБЛЕМЫ БЕЗОПАСНОСТИ")
            report.append("=" * 50)
            for issue in analysis_results['security'][:5]:
                if 'file' in issue:
                    report.append(f"📄 {issue['file']}")
                    report.append(f"   🚨 {issue.get('pattern', '')}: {issue.get('message', '')}")

        # Рекомендации по best practices
        if 'best_practices' in analysis_results:
            bp = analysis_results['best_practices']
            if bp.get('suggestions'):
                report.append("\n💡 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ")
                report.append("=" * 50)
                for suggestion in bp['suggestions'][:10]:
                    if 'file' in suggestion:
                        report.append(f"📄 {suggestion['file']}")
                        report.append(f"   💡 {suggestion.get('suggestion', '')}")

        # Общие рекомендации
        report.append("\n🎯 ОБЩИЕ РЕКОМЕНДАЦИИ")
        report.append("=" * 50)

        # Рекомендации на основе анализа
        if 'imports' in analysis_results:
            imports = analysis_results['imports']
            if 'external_imports' in imports and imports['external_imports']:
                report.append(
                    f"1. Используемые внешние библиотеки: {', '.join(sorted(imports['external_imports'])[:10])}")

        report.append("2. Добавьте README.md с описанием проекта")
        report.append("3. Создайте requirements.txt с зависимостями")
        report.append("4. Настройте .gitignore для Python проектов")
        report.append("5. Добавьте тесты для ключевых функций")

        return "\n".join(report)

    def answer_question(self, question):
        """Ответ на конкретный вопрос о проекте"""
        # Сначала проводим быстрый анализ
        quick_analysis = {}

        if "структур" in question.lower() or "структур" in question:
            quick_analysis['structure'] = self.analyze_structure()

        if "ошибк" in question.lower() or "баг" in question.lower():
            quick_analysis['errors'] = self.find_potential_errors()

        if "безопасн" in question.lower():
            quick_analysis['security'] = self.check_security_issues()

        if "производительн" in question.lower() or "скорост" in question.lower():
            quick_analysis['performance'] = self.check_performance_issues()

        if "лучш" in question.lower() or "практик" in question.lower():
            quick_analysis['best_practices'] = self.check_best_practices()

        # Если не нашли специфического анализа, делаем полный
        if not quick_analysis:
            quick_analysis = self.run_full_analysis()

        # Формируем ответ
        response_parts = []

        if "почему не работает" in question.lower():
            response_parts.append("🔧 **Возможные причины неработоспособности:**")
            response_parts.append("")

            # Проверяем основные проблемы
            errors = self.find_potential_errors()
            if errors:
                response_parts.append("**Найдены ошибки:**")
                for error in errors[:3]:
                    response_parts.append(f"- 📄 {error.get('file', 'Неизвестный файл')}: {error.get('issue', '')}")
            else:
                response_parts.append("❌ Очевидных ошибок не найдено")

            response_parts.append("")
            response_parts.append("**Что проверить:**")
            response_parts.append("1. Все ли зависимости установлены?")
            response_parts.append("2. Правильно ли настроены пути к файлам?")
            response_parts.append("3. Есть ли точки входа (main.py, app.py)?")
            response_parts.append("4. Проверьте логи ошибок при запуске")

        elif "как улучшить" in question.lower() or "улучш" in question.lower():
            response_parts.append("🚀 **Рекомендации по улучшению:**")
            response_parts.append("")

            bp = self.check_best_practices()
            if bp.get('suggestions'):
                response_parts.append("**Конкретные предложения:**")
                for suggestion in bp['suggestions'][:5]:
                    response_parts.append(f"- 📄 {suggestion.get('file', '')}: {suggestion.get('suggestion', '')}")

            response_parts.append("")
            response_parts.append("**Общие улучшения:**")
            response_parts.append("1. Добавьте документацию к функциям")
            response_parts.append("2. Разделите большие функции на маленькие")
            response_parts.append("3. Добавьте обработку ошибок")
            response_parts.append("4. Напишите тесты")
            response_parts.append("5. Используйте type hints")

        elif "объясни" in question.lower() or "как работает" in question.lower():
            response_parts.append("📚 **Объяснение проекта:**")
            response_parts.append("")

            summary = self.get_project_summary()
            response_parts.append(f"Проект состоит из {summary.get('total_py_files', 0)} Python файлов")
            response_parts.append(f"Общий объем кода: ~{summary.get('total_lines', 0)} строк")

            structure = self.analyze_structure()
            if structure.get('entry_points'):
                response_parts.append("")
                response_parts.append("**Точки входа (файлы для запуска):**")
                for entry in structure['entry_points']:
                    response_parts.append(f"- {entry}")

            imports = self.analyze_imports()
            if imports.get('external_imports'):
                response_parts.append("")
                response_parts.append("**Основные используемые библиотеки:**")
                for lib in sorted(imports['external_imports'])[:10]:
                    response_parts.append(f"- {lib}")

        else:
            # Общий ответ
            response_parts.append("🤖 **Анализ вашего вопроса:**")
            response_parts.append("")

            # Добавляем релевантную информацию из анализа
            if 'errors' in quick_analysis and quick_analysis['errors']:
                response_parts.append("**Найдены потенциальные проблемы:**")
                for error in quick_analysis['errors'][:3]:
                    response_parts.append(f"- {error.get('issue', '')}")
                response_parts.append("")

            if 'best_practices' in quick_analysis and quick_analysis['best_practices'].get('suggestions'):
                response_parts.append("**Рекомендации:**")
                for suggestion in quick_analysis['best_practices']['suggestions'][:3]:
                    response_parts.append(f"- {suggestion.get('suggestion', '')}")
                response_parts.append("")

            response_parts.append("💡 **Что еще можно сделать:**")
            response_parts.append("1. Задайте конкретный вопрос о файле или ошибке")
            response_parts.append("2. Укажите, что именно не работает")
            response_parts.append("3. Попросите объяснить конкретный участок кода")

        return "\n".join(response_parts)


class AutoAnalysisUI:
    """Автоматический интерфейс для анализа проекта"""

    def __init__(self, project_path="/content/sberai-communication-assistant"):
        self.project_path = Path(project_path)
        self.analyzer = AutoProjectAnalyzer(project_path)
        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        with gr.Blocks(title="🤖 Автоанализатор проекта", theme=gr.themes.Soft()) as self.demo:
            gr.Markdown(f"""
            # 🚀 Автоматический анализатор проекта
            ## 📍 Папка проекта: `{self.project_path}`

            Проект анализируется автоматически. Просто задайте вопрос!
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    # Информация о проекте
                    with gr.Accordion("📊 Информация о проекте", open=True):
                        project_info = self.get_project_info()
                        gr.Markdown(project_info)

                    # Вопрос пользователя
                    user_question = gr.Textbox(
                        label="💬 Ваш вопрос о проекте",
                        placeholder="Например: 'Что не так с моим проектом?', 'Как улучшить код?', 'Объясни структуру проекта'",
                        lines=3
                    )

                    # Кнопки действий
                    with gr.Row():
                        analyze_btn = gr.Button("🔍 Проанализировать проект", variant="primary", size="lg")
                        full_report_btn = gr.Button("📄 Полный отчет", variant="secondary")
                        quick_fix_btn = gr.Button("⚡ Быстрые исправления", variant="secondary")

                with gr.Column(scale=3):
                    # Результаты
                    output = gr.Markdown(
                        label="📋 Результаты анализа",
                        value="👆 Нажмите кнопку для анализа или задайте вопрос"
                    )

            # Примеры вопросов
            with gr.Accordion("📋 Примеры вопросов", open=False):
                examples = gr.Examples(
                    examples=[
                        ["Почему мой проект не работает?"],
                        ["Какие ошибки есть в моем коде?"],
                        ["Как улучшить архитектуру проекта?"],
                        ["Есть ли проблемы с безопасностью?"],
                        ["Объясни структуру моего проекта"],
                        ["Что можно оптимизировать?"],
                        ["Проверь лучшие практики"],
                        ["Найди потенциальные баги"]
                    ],
                    inputs=user_question,
                    label="Кликните для примера"
                )

            # Обработчики событий
            analyze_btn.click(
                fn=self.analyze_project,
                inputs=[user_question],
                outputs=output
            )

            user_question.submit(
                fn=self.analyze_project,
                inputs=[user_question],
                outputs=output
            )

            full_report_btn.click(
                fn=self.generate_full_report,
                inputs=[],
                outputs=output
            )

            quick_fix_btn.click(
                fn=self.suggest_quick_fixes,
                inputs=[],
                outputs=output
            )

    def get_project_info(self):
        """Получение информации о проекте для отображения"""
        try:
            summary = self.analyzer.get_project_summary()

            info_lines = []
            info_lines.append(f"**📁 Папка проекта:** `{self.project_path}`")

            if 'error' not in summary:
                info_lines.append(f"**📄 Python файлов:** {summary.get('total_py_files', 0)}")
                info_lines.append(f"**📝 Строк кода:** ~{summary.get('total_lines', 0)}")
                info_lines.append(f"**💾 Размер:** {summary.get('total_size_mb', 0)} MB")

                if summary.get('main_files'):
                    info_lines.append("\n**Основные файлы:**")
                    for file in summary['main_files'][:3]:
                        info_lines.append(f"- `{file}`")
            else:
                info_lines.append("⚠️ Папка пуста или произошла ошибка")

            return "\n".join(info_lines)
        except Exception as e:
            return f"Ошибка получения информации: {str(e)}"

    def analyze_project(self, question):
        """Анализ проекта с ответом на вопрос"""
        try:
            if not question.strip():
                question = "Проанализируй мой проект"

            response = self.analyzer.answer_question(question)

            # Добавляем заголовок
            timestamp = self._get_timestamp()
            formatted_response = f"""
## 🔍 Анализ проекта
**Время:** {timestamp}
**Вопрос:** {question}

---

{response}

---
*Анализ выполнен автоматически для папки: `{self.project_path}`*
"""
            return formatted_response
        except Exception as e:
            return f"❌ Ошибка анализа: {str(e)}"

    def generate_full_report(self):
        """Генерация полного отчета"""
        try:
            analysis = self.analyzer.run_full_analysis()
            report = self.analyzer.generate_report(analysis)

            timestamp = self._get_timestamp()
            formatted_report = f"""
# 📊 ПОЛНЫЙ ОТЧЕТ ПО ПРОЕКТУ
**Время анализа:** {timestamp}
**Путь к проекту:** `{self.project_path}`

---

{report}

---
*Сгенерировано автоматически. Для деталей задайте конкретный вопрос.*
"""
            return formatted_report
        except Exception as e:
            return f"❌ Ошибка генерации отчета: {str(e)}"

    def suggest_quick_fixes(self):
        """Предложение быстрых исправлений"""
        try:
            # Собираем быстрые исправления
            fixes = []

            # Проверяем наличие requirements.txt
            if not (self.project_path / "requirements.txt").exists():
                fixes.append("📝 **Создать requirements.txt:**\n```bash\npip freeze > requirements.txt\n```")

            # Проверяем наличие README.md
            if not (self.project_path / "README.md").exists():
                fixes.append(
                    "📖 **Создать README.md:**\n```markdown\n# Название проекта\n\n## Описание\n\n## Установка\n\n## Использование\n```")

            # Проверяем наличие .gitignore
            if not (self.project_path / ".gitignore").exists():
                fixes.append(
                    "🚫 **Создать .gitignore для Python:**\n```\n__pycache__/\n*.py[cod]\n*$py.class\n*.so\n.Python\nenv/\nvenv/\n```")

            # Анализируем код на быстрые исправления
            errors = self.analyzer.find_potential_errors()
            if errors:
                fixes.append("🔧 **Быстрые исправления кода:**")
                for error in errors[:3]:
                    fixes.append(f"- **{error.get('file', 'Файл')}**: {error.get('issue', '')}")

            if not fixes:
                fixes.append("✅ Отличная работа! Явных проблем для быстрого исправления не найдено.")

            timestamp = self._get_timestamp()
            return f"""
# ⚡ Быстрые исправления
**Время:** {timestamp}

---

{chr(10).join(fixes)}

---
*Эти исправления помогут улучшить проект. Для детального анализа задайте конкретный вопрос.*
"""
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def _get_timestamp(self):
        """Получение временной метки"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def launch(self):
        """Запуск интерфейса"""
        return self.demo.launch(debug=True, share=True)


# ===================== ЗАПУСК СИСТЕМЫ =====================

print("🚀 Запускаю автоматический анализатор проекта...")
print(f"📁 Анализирую папку: /content/sberai-communication-assistant")
print("⏳ Инициализация...")

# Проверяем существование папки
import os

project_path = "/content/sberai-communication-assistant"

if not os.path.exists(project_path):
    print("⚠️  Папка проекта не найдена. Создаю...")
    os.makedirs(project_path, exist_ok=True)

    # Создаем пример файла, если папка пуста
    example_file = os.path.join(project_path, "example.py")
    with open(example_file, "w") as f:
        f.write('''"""
Пример файла для анализа
"""

def hello_world():
    """Функция приветствия"""
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
''')
    print(f"✅ Создана папка и пример файла: {example_file}")

# Запускаем интерфейс
try:
    ui = AutoAnalysisUI(project_path)
    print("✅ Анализатор инициализирован!")
    print("🌐 Открываю интерфейс...")
    ui.launch()
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")
    print("\n🔧 Альтернативный вариант - консольный анализ:")

    # Консольный вариант если Gradio не запускается
    analyzer = AutoProjectAnalyzer(project_path)

    print("\n📊 Быстрая сводка проекта:")
    summary = analyzer.get_project_summary()
    print(f"   Файлов .py: {summary.get('total_py_files', 0)}")
    print(f"   Строк кода: {summary.get('total_lines', 0)}")

    print("\n❌ Поиск ошибок...")
    errors = analyzer.find_potential_errors()
    if errors:
        for error in errors[:5]:
            print(f"   📄 {error.get('file', '')}: {error.get('issue', '')}")
    else:
        print("   ✅ Очевидных ошибок не найдено")

    print("\n💡 Для детального анализа запустите:")
    print("   analyzer.run_full_analysis()")
    print("   analyzer.generate_report(analysis)")