"""
database.py - Работа с базой данных тренировок
Поддерживает названия тренировок, шаблоны и статистику
"""

import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных тренировок"""

    def __init__(self, db_name="training.db"):
        """Инициализация подключения к базе данных"""
        self.db_name = db_name
        self.init_db()
        logger.info(f"✅ База данных инициализирована: {db_name}")

    def get_connection(self):
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Создание таблиц, если их нет (с поддержкой названий тренировок)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Проверяем, существует ли таблица workouts
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='workouts'
                ''')
                table_exists = cursor.fetchone()

                if table_exists:
                    # Проверяем структуру существующей таблицы
                    cursor.execute('PRAGMA table_info(workouts)')
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]

                    # Если нет колонки workout_name - пересоздаём таблицу
                    if 'workout_name' not in column_names:
                        logger.warning("⚠️ Обновляем структуру таблицы workouts...")

                        # Переименовываем старую таблицу
                        cursor.execute('ALTER TABLE workouts RENAME TO workouts_old')

                        # Создаём новую таблицу с нужной структурой
                        cursor.execute('''
                            CREATE TABLE workouts (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                workout_name TEXT NOT NULL DEFAULT 'Тренировка',
                                workout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                exercises TEXT NOT NULL,
                                notes TEXT,
                                FOREIGN KEY (user_id) REFERENCES users (user_id)
                            )
                        ''')

                        # Переносим данные из старой таблицы (если есть)
                        try:
                            cursor.execute('''
                                INSERT INTO workouts (id, user_id, workout_date, exercises)
                                SELECT id, user_id, workout_date, exercises 
                                FROM workouts_old
                            ''')
                            logger.info("✅ Данные перенесены в новую таблицу")
                        except Exception as e:
                            logger.error(f"❌ Ошибка переноса данных: {e}")

                        # Удаляем старую таблицу
                        cursor.execute('DROP TABLE IF EXISTS workouts_old')
                else:
                    # Создаём новую таблицу с правильной структурой
                    cursor.execute('''
                        CREATE TABLE workouts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            workout_name TEXT NOT NULL DEFAULT 'Тренировка',
                            workout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            exercises TEXT NOT NULL,
                            notes TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (user_id)
                        )
                    ''')
                    logger.info("✅ Таблица workouts создана")

                # Таблица для шаблонов тренировок
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workout_templates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        template_name TEXT NOT NULL,
                        exercises TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

                conn.commit()
                logger.info("✅ Все таблицы проверены и готовы")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise

    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Добавить нового пользователя или обновить существующего"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, created_at)
                    VALUES (?, ?, ?, ?, COALESCE(
                        (SELECT created_at FROM users WHERE user_id = ?),
                        CURRENT_TIMESTAMP
                    ))
                ''', (user_id, username, first_name, last_name, user_id))
                conn.commit()
                logger.info(f"✅ Пользователь {user_id} добавлен/обновлён")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя {user_id}: {e}")
            return False

    def save_workout(self, user_id, workout_name, exercises):
        """Сохранить тренировку с названием"""
        try:
            # Преобразуем список упражнений в JSON строку
            exercises_json = json.dumps(exercises, ensure_ascii=False)

            logger.info(f"💾 Сохраняем тренировку для user {user_id}")
            logger.info(f"📝 Название: {workout_name}")
            logger.info(f"📊 Упражнений: {len(exercises)}")

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                if not cursor.fetchone():
                    logger.warning(f"⚠️ Пользователь {user_id} не найден, создаём...")
                    self.add_user(user_id)

                # Вставляем тренировку
                cursor.execute('''
                    INSERT INTO workouts (user_id, workout_name, exercises)
                    VALUES (?, ?, ?)
                ''', (user_id, workout_name, exercises_json))

                conn.commit()
                workout_id = cursor.lastrowid

                logger.info(f"✅ Тренировка {workout_id} сохранена в БД")

                # Проверяем, что запись действительно есть
                cursor.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,))
                result = cursor.fetchone()
                if result:
                    logger.info(f"✅ Проверка: тренировка {workout_id} найдена")
                else:
                    logger.error(f"❌ Тренировка {workout_id} не найдена после сохранения!")

                return workout_id

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения тренировки: {e}")
            raise

    def get_user_workouts(self, user_id, limit=20):
        """Получить все тренировки пользователя"""
        try:
            logger.info(f"📖 Запрос тренировок для пользователя {user_id}")

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
                logger.info(f"👤 Пользователь в БД: {user}")

                # Получаем тренировки
                cursor.execute('''
                    SELECT id, workout_name, workout_date, exercises, notes
                    FROM workouts
                    WHERE user_id = ?
                    ORDER BY workout_date DESC
                    LIMIT ?
                ''', (user_id, limit))

                rows = cursor.fetchall()
                logger.info(f"📊 Найдено тренировок: {len(rows)}")

                workouts = []
                for row in rows:
                    try:
                        workout = {
                            'id': row[0],
                            'name': row[1] if row[1] else 'Тренировка',
                            'date': row[2],
                            'exercises': json.loads(row[3]) if row[3] else [],
                            'notes': row[4] or ''
                        }
                        workouts.append(workout)
                        logger.info(
                            f"  • Тренировка {workout['id']}: {workout['name']} ({len(workout['exercises'])} упр.)")
                    except Exception as e:
                        logger.error(f"❌ Ошибка парсинга тренировки {row[0]}: {e}")
                        # Добавляем с пустыми упражнениями, чтобы не ломать вывод
                        workouts.append({
                            'id': row[0],
                            'name': row[1] or 'Тренировка',
                            'date': row[2],
                            'exercises': [],
                            'notes': 'Ошибка загрузки'
                        })

                return workouts

        except Exception as e:
            logger.error(f"❌ Ошибка получения тренировок: {e}")
            return []

    def get_workout_by_id(self, workout_id):
        """Получить конкретную тренировку по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, workout_name, workout_date, exercises, notes
                    FROM workouts
                    WHERE id = ?
                ''', (workout_id,))

                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'user_id': row[1],
                        'name': row[2] or 'Тренировка',
                        'date': row[3],
                        'exercises': json.loads(row[4]) if row[4] else [],
                        'notes': row[5] or ''
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения тренировки {workout_id}: {e}")
            return None

    def update_workout_name(self, workout_id, new_name):
        """Изменить название тренировки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE workouts SET workout_name = ? WHERE id = ?
                ''', (new_name, workout_id))
                conn.commit()
                logger.info(f"✅ Название тренировки {workout_id} изменено на '{new_name}'")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка изменения названия: {e}")
            return False

    def delete_workout(self, workout_id):
        """Удалить тренировку"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
                conn.commit()
                logger.info(f"✅ Тренировка {workout_id} удалена")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления тренировки: {e}")
            return False

    def save_template(self, user_id, template_name, exercises):
        """Сохранить шаблон тренировки"""
        try:
            exercises_json = json.dumps(exercises, ensure_ascii=False)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO workout_templates (user_id, template_name, exercises)
                    VALUES (?, ?, ?)
                ''', (user_id, template_name, exercises_json))
                conn.commit()
                template_id = cursor.lastrowid
                logger.info(f"✅ Шаблон '{template_name}' сохранён (ID: {template_id})")
                return template_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения шаблона: {e}")
            return None

    def get_templates(self, user_id):
        """Получить все шаблоны пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, template_name, exercises, created_at
                    FROM workout_templates
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))

                templates = []
                for row in cursor.fetchall():
                    template = {
                        'id': row[0],
                        'name': row[1],
                        'exercises': json.loads(row[2]) if row[2] else [],
                        'created_at': row[3]
                    }
                    templates.append(template)

                logger.info(f"📋 Загружено {len(templates)} шаблонов для user {user_id}")
                return templates
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки шаблонов: {e}")
            return []

    def get_workout_stats(self, user_id):
        """Получить статистику тренировок"""
        try:
            logger.info(f"📊 Запрос статистики для пользователя {user_id}")

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Общее количество тренировок
                cursor.execute('SELECT COUNT(*) FROM workouts WHERE user_id = ?', (user_id,))
                total_workouts = cursor.fetchone()[0] or 0

                # Количество упражнений и вес
                cursor.execute('SELECT exercises FROM workouts WHERE user_id = ?', (user_id,))
                all_exercises = cursor.fetchall()

                total_exercises = 0
                total_weight = 0
                unique_exercises = set()

                for ex_json in all_exercises:
                    if ex_json[0]:
                        try:
                            exercises = json.loads(ex_json[0])
                            total_exercises += len(exercises)
                            for ex in exercises:
                                weight = ex.get('weight', 0)
                                sets = ex.get('sets', 0)
                                reps = ex.get('reps', 0)
                                total_weight += weight * sets * reps
                                if ex.get('name'):
                                    unique_exercises.add(ex.get('name', '').lower())
                        except:
                            continue

                # Последняя тренировка
                cursor.execute('''
                    SELECT workout_name, workout_date FROM workouts 
                    WHERE user_id = ? 
                    ORDER BY workout_date DESC LIMIT 1
                ''', (user_id,))
                last = cursor.fetchone()

                stats = {
                    'total_workouts': total_workouts,
                    'total_exercises': total_exercises,
                    'total_weight': round(total_weight, 1),
                    'unique_exercises': len(unique_exercises),
                    'last_workout': last[1] if last else None,
                    'last_workout_name': last[0] if last else None
                }

                logger.info(f"📊 Статистика: {stats}")
                return stats

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_workouts': 0,
                'total_exercises': 0,
                'total_weight': 0,
                'unique_exercises': 0,
                'last_workout': None,
                'last_workout_name': None
            }

    def clear_user_data(self, user_id):
        """Очистить все данные пользователя (для тестирования)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM workouts WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM workout_templates WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
                logger.info(f"✅ Данные пользователя {user_id} очищены")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")
            return False