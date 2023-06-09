import sqlite3
from aiogram.dispatcher.filters.state import StatesGroup, State
import json


class UserState(StatesGroup):  # класс для состояний FSM
    jira_token = State()


class Database:

    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

        # Создать таблицу, если её нет
        if not bool(self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users_tokens_data';"
                                        ).fetchone()):
            self.cursor.execute("""
                CREATE TABLE users_tokens_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER UNIQUE,
                    jira_token TEXT,
                    user_data TEXT,
                    user_name TEXT 
                    );                                      
                """)
            self.connection.commit()

    @staticmethod
    def change_type(user_data: dict):
        return str(user_data)  # ->str

    def check_user_id_exist(self, user_id):
        """ Проверить наличие user_id  в базе :return bool """

        with self.connection:
            result = self.cursor.execute(f"SELECT user_id FROM 'users_tokens_data' WHERE user_id = ?", (user_id,)).fetchmany(1)
            return bool(len(result))

    def add_new_row(self, user_id, jira_token, user_data, user_name):
        """ Добавить новую строку """

        user_data = self.change_type(user_data)
        with self.connection:
            return self.cursor.execute(
                "INSERT INTO 'users_tokens_data' ('user_id', 'jira_token', 'user_data', 'user_name') VALUES(?, ?, ?, ?)",
                (user_id, jira_token, user_data, user_name,))

    def get_all_data(self):
        """ Достать все записи из БД :return list(tuple1, tuple2, tuple3) | len(tuple) == 4 """

        with self.connection:
            return self.cursor.execute("SELECT user_id, jira_token, user_data, user_name FROM 'users_tokens_data'").fetchall()

    def update_user_data(self, user_id, user_data):
        """Обновить ячейку user_data"""

        # user_data = self.change_type(user_data)
        user_data = json.dumps(user_data, ensure_ascii=False)
        with self.connection:
            return self.cursor.execute(
                f"UPDATE 'users_tokens_data' SET user_data = '{user_data}' WHERE user_id = {user_id}"
            )

    def del_row(self, user_id):
        """ Удалить строку """

        with self.connection:
            return self.cursor.execute(
                f"DELETE from 'users_tokens_data' WHERE user_id = {user_id}"
            )

    def get_user_id(self, user_name):
        """ Получить tg_id по user_name из jira"""
        with self.connection:
            result = self.cursor.execute(f"SELECT user_id FROM 'users_tokens_data' WHERE user_name = ?", (user_name,)).fetchmany(1)
            if bool(result):
                return result[0][0]
