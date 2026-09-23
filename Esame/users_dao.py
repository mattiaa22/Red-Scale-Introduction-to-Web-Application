import sqlite3

DB_NAME = "guild.db" 

def new_user(name, email, password, role, priority):

    query = "INSERT INTO users (name, email, password, role, priority) VALUES (?, ?, ?, ?, ?)"

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(query, (name, email, password, role, priority))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        conn.rollback()
        success = False
    finally:
        cursor.close()
        conn.close()

    return success


def get_user_by_id(user_id):

    query = "SELECT * FROM users WHERE id = ?"

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(query, (user_id,))
    db_user = cursor.fetchone()

    conn.commit()
    cursor.close()
    conn.close()

    return db_user


def get_user_by_email(email):

    query = "SELECT * FROM users WHERE email = ?"

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(query, (email,))
    db_user = cursor.fetchone()

    conn.commit()
    cursor.close()
    conn.close()

    return db_user


def get_adventurers_for_council():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
        SELECT u.id, u.name, u.email, 
               COALESCE(COUNT(p.id), 0) as total_participations
        FROM users u
        LEFT JOIN participations p ON u.id = p.user_id
        WHERE u.priority = 0
        GROUP BY u.id
        ORDER BY total_participations DESC
    """
    cursor.execute(query)
    adventurers = cursor.fetchall()
    conn.close()
    return [dict(row) for row in adventurers]