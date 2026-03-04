"""
database.py - Полная версия с библиотекой упражнений и всеми методами
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
        self.init_exercises_library()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Создание всех таблиц"""
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

            # Библиотека упражнений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exercises_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    muscle_group TEXT NOT NULL,
                    exercise_name TEXT NOT NULL,
                    description TEXT,
                    default_sets INTEGER DEFAULT 3,
                    default_reps INTEGER DEFAULT 10,
                    difficulty TEXT DEFAULT 'medium',
                    equipment TEXT,
                    UNIQUE(muscle_group, exercise_name)
                )
            ''')

            # Сохранённые планы пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_name TEXT NOT NULL,
                    focus_muscle TEXT,
                    week_plan TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.commit()
            logger.info("✅ Все таблицы созданы")

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

    def init_exercises_library(self):
        """Заполняем библиотеку упражнений"""
        exercises = [
            # ГРУДЬ
            ('грудь', 'Жим штанги лёжа', 'Базовое упражнение для всей груди', 4, 10, 'medium', 'штанга'),
            ('грудь', 'Жим гантелей на наклонной', 'Акцент на верх груди', 3, 12, 'medium', 'гантели'),
            ('грудь', 'Сведение рук в кроссовере', 'Изолированная работа', 3, 15, 'easy', 'тренажёр'),
            ('грудь', 'Отжимания на брусьях', 'Низ груди и трицепс', 3, 10, 'hard', 'брусья'),
            ('грудь', 'Жим в хаммере', 'Машина для грудных', 3, 12, 'easy', 'тренажёр'),

            # СПИНА
            ('спина', 'Подтягивания широким хватом', 'Ширина спины', 4, 8, 'hard', 'турник'),
            ('спина', 'Тяга штанги в наклоне', 'Толщина спины', 4, 10, 'medium', 'штанга'),
            ('спина', 'Тяга верхнего блока', 'Широчайшие мышцы', 3, 12, 'easy', 'тренажёр'),
            ('спина', 'Тяга гантели к поясу', 'Детализация', 3, 12, 'medium', 'гантели'),
            ('спина', 'Мёртвая тяга', 'Вся спина и ноги', 5, 5, 'hard', 'штанга'),

            # НОГИ
            ('ноги', 'Приседания со штангой', 'Квадрицепс, ягодицы', 5, 8, 'hard', 'штанга'),
            ('ноги', 'Румынская тяга', 'Бицепс бедра', 4, 10, 'medium', 'штанга'),
            ('ноги', 'Жим ногами', 'Масса ног', 3, 15, 'easy', 'тренажёр'),
            ('ноги', 'Выпады с гантелями', 'Ягодицы', 3, 12, 'medium', 'гантели'),
            ('ноги', 'Сгибания ног лёжа', 'Бицепс бедра', 3, 15, 'easy', 'тренажёр'),

            # ПЛЕЧИ
            ('плечи', 'Армейский жим стоя', 'Передняя и средняя дельта', 4, 8, 'hard', 'штанга'),
            ('плечи', 'Махи гантелями в стороны', 'Средняя дельта', 3, 15, 'easy', 'гантели'),
            ('плечи', 'Тяга штанги к подбородку', 'Средняя и задняя дельта', 3, 12, 'medium', 'штанга'),
            ('плечи', 'Разведение рук в наклоне', 'Задняя дельта', 3, 15, 'medium', 'гантели'),

            # БИЦЕПС
            ('бицепс', 'Подъём штанги на бицепс', 'Масса бицепса', 3, 10, 'medium', 'штанга'),
            ('бицепс', 'Молотки с гантелями', 'Брахиалис', 3, 12, 'easy', 'гантели'),
            ('бицепс', 'Подъём гантелей на бицепс сидя', 'Пик бицепса', 3, 10, 'medium', 'гантели'),

            # ТРИЦЕПС
            ('трицепс', 'Французский жим лёжа', 'Длинная головка', 3, 10, 'medium', 'штанга'),
            ('трицепс', 'Отжимания на трицепс', 'Все головки', 3, 12, 'hard', 'брусья'),
            ('трицепс', 'Разгибание рук на блоке', 'Латеральная головка', 3, 15, 'easy', 'тренажёр'),

            # ПРЕСС
            ('пресс', 'Скручивания на римском стуле', 'Верх пресса', 3, 20, 'medium', 'тренажёр'),
            ('пресс', 'Подъём ног в висе', 'Низ пресса', 3, 15, 'hard', 'турник'),
            ('пресс', 'Планка', 'Кор', 3, 60, 'medium', 'коврик')
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR IGNORE INTO exercises_library 
                (muscle_group, exercise_name, description, default_sets, default_reps, difficulty, equipment)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', exercises)
            conn.commit()
            logger.info(f"✅ Библиотека упражнений заполнена ({len(exercises)} упражнений)")

    def save_workout(self, user_id, workout_name, exercises):
        """Сохранить тренировку"""
        try:
            exercises_json = json.dumps(exercises, ensure_ascii=False)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                if not cursor.fetchone():
                    self.add_user(user_id)

                cursor.execute('''
                    INSERT INTO workouts (user_id, workout_name, exercises)
                    VALUES (?, ?, ?)
                ''', (user_id, workout_name, exercises_json))

                conn.commit()
                workout_id = cursor.lastrowid
                logger.info(f"✅ Тренировка {workout_id} сохранена")
                return workout_id

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения тренировки: {e}")
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
                    'exercises': json.loads(row[3]) if row[3] else []
                })
            return workouts

    def get_exercises_by_muscle(self, muscle_group, limit=4):
        """Получить упражнения для группы мышц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT exercise_name, default_sets, default_reps, description, equipment
                FROM exercises_library
                WHERE muscle_group = ?
                ORDER BY RANDOM()
                LIMIT ?
            ''', (muscle_group, limit))

            return cursor.fetchall()

    def generate_workout(self, muscle_group, intensity='medium'):
        """Сгенерировать тренировку для группы мышц"""
        counts = {'easy': 3, 'medium': 4, 'hard': 5}
        count = counts.get(intensity, 4)

        exercises = self.get_exercises_by_muscle(muscle_group, count)

        return [{
            'name': ex[0],
            'sets': ex[1],
            'reps': ex[2],
            'weight': 0,
            'equipment': ex[4]
        } for ex in exercises]

    def generate_weekly_plan(self, user_id, focus='все'):
        """Сгенерировать план на неделю"""

        logger.info(f"📋 Генерация плана для user {user_id} с фокусом: {focus}")

        # Базовая структура для всех дней
        plan = {
            'понедельник': {'name': 'Понедельник', 'exercises': []},
            'вторник': {'name': 'Вторник', 'exercises': []},
            'среда': {'name': 'Среда', 'exercises': []},
            'четверг': {'name': 'Четверг', 'exercises': []},
            'пятница': {'name': 'Пятница', 'exercises': []},
            'суббота': {'name': 'Суббота', 'exercises': []},
            'воскресенье': {'name': 'Воскресенье', 'exercises': []}
        }

        if focus == 'грудь':
            plan['понедельник']['exercises'] = self.generate_workout('грудь', 'hard') + self.generate_workout('трицепс',
                                                                                                              'medium')
            plan['среда']['exercises'] = self.generate_workout('спина', 'medium') + self.generate_workout('бицепс',
                                                                                                          'medium')
            plan['пятница']['exercises'] = self.generate_workout('ноги', 'hard') + self.generate_workout('плечи',
                                                                                                         'medium')
            plan['суббота']['exercises'] = self.generate_workout('грудь', 'medium')

        elif focus == 'спина':
            plan['понедельник']['exercises'] = self.generate_workout('спина', 'hard')
            plan['вторник']['exercises'] = self.generate_workout('грудь', 'medium') + self.generate_workout('плечи',
                                                                                                            'easy')
            plan['четверг']['exercises'] = self.generate_workout('спина', 'medium')
            plan['пятница']['exercises'] = self.generate_workout('ноги', 'medium')
            plan['суббота']['exercises'] = self.generate_workout('бицепс', 'easy') + self.generate_workout('трицепс',
                                                                                                           'easy')

        elif focus == 'ноги':
            plan['понедельник']['exercises'] = self.generate_workout('ноги', 'hard')
            plan['вторник']['exercises'] = self.generate_workout('грудь', 'medium') + self.generate_workout('трицепс',
                                                                                                            'easy')
            plan['четверг']['exercises'] = self.generate_workout('ноги', 'medium')
            plan['пятница']['exercises'] = self.generate_workout('спина', 'medium') + self.generate_workout('бицепс',
                                                                                                            'easy')
            plan['суббота']['exercises'] = self.generate_workout('плечи', 'easy') + self.generate_workout('пресс',
                                                                                                          'medium')

        elif focus == 'руки':
            plan['понедельник']['exercises'] = self.generate_workout('бицепс', 'hard') + self.generate_workout(
                'трицепс', 'hard')
            plan['вторник']['exercises'] = self.generate_workout('грудь', 'medium')
            plan['среда']['exercises'] = self.generate_workout('спина', 'medium')
            plan['четверг']['exercises'] = self.generate_workout('плечи', 'medium')
            plan['пятница']['exercises'] = self.generate_workout('бицепс', 'medium') + self.generate_workout('трицепс',
                                                                                                             'medium')
            plan['суббота']['exercises'] = self.generate_workout('ноги', 'medium')

        else:  # баланс
            plan['понедельник']['exercises'] = self.generate_workout('грудь', 'medium') + self.generate_workout(
                'трицепс', 'easy')
            plan['вторник']['exercises'] = self.generate_workout('спина', 'medium') + self.generate_workout('бицепс',
                                                                                                            'easy')
            plan['среда']['exercises'] = self.generate_workout('ноги', 'medium')
            plan['четверг']['exercises'] = self.generate_workout('плечи', 'medium') + self.generate_workout('пресс',
                                                                                                            'easy')
            plan['пятница']['exercises'] = self.generate_workout('бицепс', 'medium') + self.generate_workout('трицепс',
                                                                                                             'medium')
            plan['суббота']['exercises'] = (
                    self.generate_workout('грудь', 'easy') +
                    self.generate_workout('спина', 'easy') +
                    self.generate_workout('ноги', 'easy')
            )

        # Логируем результат для отладки
        days_with_exercises = [day for day in plan if plan[day]['exercises']]
        logger.info(f"✅ План сгенерирован. Дни с упражнениями: {days_with_exercises}")

        return plan

    def get_workout_stats(self, user_id):
        """Получить статистику пользователя"""
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
            'total_weight': round(total_weight, 1)
        }