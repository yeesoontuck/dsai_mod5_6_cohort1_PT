import sqlite3

class UserDB:
    def __init__(self, db_path='user.db'):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def read_users(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY name COLLATE NOCASE')
            return cursor.fetchall()

    def read_user(self, name, timestamp):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE name = ? AND timestamp = ? LIMIT 1', (name, timestamp))
            return cursor.fetchone()

    def update_user(self, orig_name, orig_timestamp, username, t):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET name = ?, timestamp = ? where name = ? and timestamp = ?', (username, t, orig_name, orig_timestamp))
            conn.commit()

    def delete_user(self, name, timestamp):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users where name = ? and timestamp = ?', (name, timestamp))
            conn.commit()