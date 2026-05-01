import sqlite3

def init_database():
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'pending',
            role TEXT DEFAULT 'user'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            config_key TEXT PRIMARY KEY,
            config_value TEXT
        )
    ''')
    try:
        cursor.execute("INSERT INTO users (student_id, name, status, role) VALUES (?, ?, ?, ?)",
                       ('admin', '管理员', 'approved', 'admin'))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()