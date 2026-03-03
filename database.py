"""
database.py - База данных с поддержкой удаления
"""

import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name="training.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
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

            conn.commit()
            logger.info("✅ База данных готова")

    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()

    def save_workout(self, user_id, workout_name, exercises):
        """Сохранить тренировку"""
        try:
            exercises_json = json.dumps(exercises, ensure_ascii=False)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем пользователя
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                if not cursor.fetchone():
                    cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))

                # Сохраняем тренировку
                cursor.execute('''
                    INSERT INTO workouts (user_id, workout_name, exercises)
                    VALUES (?, ?, ?)
                ''', (user_id, workout_name, exercises_json))

                conn.commit()
                workout_id = cursor.lastrowid
                logger.info(f"✅ Тренировка {workout_id} сохранена")
                return workout_id

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения: {e}")
            return None

    def get_user_workouts(self, user_id, limit=20):
        """Получить тренировки пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, workout_name, workout_date, exercises
                FROM workouts
                WHERE user_id = ?
                ORDER BY workout_date DESC
                LIMIT ?
            ''', (user_id, limit))

            workouts = []
            for row in cursor.fetchall():
                workouts.append({
                    'id': row[0],
                    'name': row[1],
                    'date': row[2],
                    'exercises': json.loads(row[3])
                })

            return workouts

    def delete_workout(self, workout_id, user_id=None):
        """Удалить тренировку по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if user_id:
                    cursor.execute('DELETE FROM workouts WHERE id = ? AND user_id = ?',
                                   (workout_id, user_id))
                else:
                    cursor.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))

                conn.commit()
                deleted = cursor.rowcount

                if deleted > 0:
                    logger.info(f"✅ Тренировка {workout_id} удалена")
                    return True
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка удаления: {e}")
            return False

    def get_workout_stats(self, user_id):
        """Получить статистику"""
        workouts = self.get_user_workouts(user_id, limit=1000)

        total_workouts = len(workouts)
        total_exercises = sum(len(w['exercises']) for w in workouts)
        total_weight = sum(
            ex.get('weight', 0) * ex.get('sets', 0) * ex.get('reps', 0)
            for w in workouts for ex in w['exercises']
        )

        return {
            'total_workouts': total_workouts,
            'total_exercises': total_exercises,
            'total_weight': round(total_weight, 1),
            'unique_exercises': len(set(
                ex.get('name', '').lower()
                for w in workouts for ex in w['exercises']
            ))
        }
