"""
database.py - Работа с базой данных тренировок
Поддерживает названия тренировок, шаблоны, статистику и удаление
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
        """Создание таблиц, если их нет"""
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

                # Таблица тренировок
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        workout_name TEXT NOT NULL DEFAULT 'Тренировка',
                        workout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        exercises TEXT NOT NULL,
                        notes TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

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
        """Сохранить тренировку в базу данных"""
        try:
            logger.info(f"💾 Попытка сохранить тренировку для user {user_id}")
            logger.info(f"📝 Название: {workout_name}")
            logger.info(f"📊 Упражнений: {len(exercises)}")

            # Преобразуем упражнения в JSON
            exercises_json = json.dumps(exercises, ensure_ascii=False)
            logger.info(f"🔧 JSON упражнений: {exercises_json[:200]}...")

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем, существует ли пользователь
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                if not cursor.fetchone():
                    logger.warning(f"⚠️ Пользователь {user_id} не найден, создаём...")
                    cursor.execute('''
                        INSERT INTO users (user_id) VALUES (?)
                    ''', (user_id,))

                # Вставляем тренировку
                cursor.execute('''
                    INSERT INTO workouts (user_id, workout_name, exercises)
                    VALUES (?, ?, ?)
                ''', (user_id, workout_name, exercises_json))

                conn.commit()
                workout_id = cursor.lastrowid
                logger.info(f"✅ Тренировка {workout_id} успешно сохранена в БД")

                # Проверяем, что запись действительно есть
                cursor.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,))
                result = cursor.fetchone()
                logger.info(f"🔍 Проверка: тренировка {workout_id} найдена")

                return workout_id

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения тренировки: {e}", exc_info=True)
            return None

    def get_user_workouts(self, user_id, limit=20):
        """Получить все тренировки пользователя"""
        try:
            logger.info(f"📖 Запрос тренировок для пользователя {user_id}")

            with self.get_connection() as conn:
                cursor = conn.cursor()
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
                    except Exception as e:
                        logger.error(f"❌ Ошибка парсинга тренировки {row[0]}: {e}")
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

    # ========== НОВЫЙ МЕТОД ДЛЯ УДАЛЕНИЯ ТРЕНИРОВКИ ==========
    def delete_workout(self, workout_id, user_id=None):
        """
        Удалить тренировку по ID
        Если указан user_id, проверяет принадлежность тренировки
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Если указан user_id, проверяем принадлежность
                if user_id:
                    cursor.execute('SELECT user_id FROM workouts WHERE id = ?', (workout_id,))
                    result = cursor.fetchone()
                    if not result:
                        logger.warning(f"⚠️ Тренировка {workout_id} не найдена")
                        return False
                    if result[0] != user_id:
                        logger.warning(f"⚠️ Попытка удалить чужую тренировку {workout_id}")
                        return False

                # Удаляем тренировку
                cursor.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
                conn.commit()
                deleted = cursor.rowcount

                if deleted > 0:
                    logger.info(f"✅ Тренировка {workout_id} успешно удалена")
                    return True
                else:
                    logger.warning(f"⚠️ Тренировка {workout_id} не найдена")
                    return False

        except Exception as e:
            logger.error(f"❌ Ошибка удаления тренировки {workout_id}: {e}", exc_info=True)
            return False

    def get_workout_stats(self, user_id):
        """Получить статистику тренировок"""
        try:
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