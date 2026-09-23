import sqlite3

DB_NAME = "guild.db"

def get_db_connection():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_quests():
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quests ORDER BY title")
    quests = cursor.fetchall()
    conn.close()
    return quests


def get_quest_by_id(quest_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
    quest = cursor.fetchone()
    conn.close()
    return quest


def create_quest(title, duration, q_type, difficulty, description, img):

    query = """INSERT INTO quests 
               (title, duration, type, difficulty, description, img) 
               VALUES (?, ?, ?, ?, ?, ?)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (title, duration, q_type, difficulty, description, img))
    conn.commit()
    conn.close()


def get_sessions_by_quest(quest_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE quest_id = ? ORDER BY day, time", (quest_id,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions


def get_quest_by_session(session_id):

    query = """
        SELECT q.* FROM quests q
        JOIN sessions s ON q.id = s.quest_id
        WHERE s.id = ?
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result["id"]
    return None


def get_master_sessions():

    query = """
        SELECT s.id as session_id, q.title, s.day, s.time, s.location 
        FROM sessions s
        JOIN quests q ON s.quest_id = q.id
        ORDER BY 
            CASE s.day 
                WHEN 'Monday' THEN 1 
                WHEN 'Tuesday' THEN 2 
                WHEN 'Wednesday' THEN 3 
                WHEN 'Thursday' THEN 4 
                WHEN 'Friday' THEN 5 
                WHEN 'Saturday' THEN 6 
                WHEN 'Sunday' THEN 7 
            END, 
            s.time ASC
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for session in sessions:
        session["rem_warrior"] = get_available_role_spots(session["session_id"], 1)
        session["rem_mage"] = get_available_role_spots(session["session_id"], 2)
        session["rem_healer"] = get_available_role_spots(session["session_id"], 3)
        session["total_participants"] = count_participants(session["session_id"])
        
    return sessions


def get_session_by_id(session_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    conn.close()
    return session

def create_session(quest_id, day, time, location):

    query = "INSERT INTO sessions (quest_id, day, time, location) VALUES (?, ?, ?, ?)"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (quest_id, day, time, location))
    conn.commit()
    conn.close()


def update_session(session_id, day, time, location):

    query = """
        UPDATE sessions 
        SET day = ?, time = ?, location = ? 
        WHERE id = ?
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (day, time, location, session_id))
    conn.commit()
    conn.close()

def get_booked_spots(session_id, role):

    query = """
        SELECT SUM(places) as total_booked
        FROM participations 
        WHERE session_id = ? AND role = ?
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    print(f"{role} porcodioooooooooooo")
    cursor.execute(query, (session_id, role))
    result = cursor.fetchone()
    conn.close()
    if result["total_booked"] is None:
        return 0
    return result["total_booked"]


def delete_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def check_session_overlap(quest_id, day, time_str, location, exclude_session_id=None):

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT duration FROM quests WHERE id = ?", (quest_id,))
    quest = cursor.fetchone()
    if not quest:
        conn.close()
        return False
    
    new_duration_minutes = quest["duration"]
    
    try:
        h, m = map(int, time_str.split(':'))
        new_start = h * 60 + m
        new_end = new_start + new_duration_minutes
    except (ValueError, AttributeError):
        conn.close()
        return False

    if exclude_session_id:
        query = """
            SELECT s.id, s.time, q.duration 
            FROM sessions s
            JOIN quests q ON s.quest_id = q.id
            WHERE s.day = ? AND s.location = ? AND s.id != ?
        """
        cursor.execute(query, (day, location, exclude_session_id))
    else:
        query = """
            SELECT s.id, s.time, q.duration 
            FROM sessions s
            JOIN quests q ON s.quest_id = q.id
            WHERE s.day = ? AND s.location = ?
        """
        cursor.execute(query, (day, location))
        
    existing_sessions = cursor.fetchall()
    conn.close()

    for session in existing_sessions:
        try:
            eh, em = map(int, session["time"].split(':'))
            exist_start = eh * 60 + em
            exist_duration_minutes = session["duration"]
            exist_end = exist_start + exist_duration_minutes
            if new_start < exist_end and exist_start < new_end:
                return True 
        except (ValueError, KeyError, TypeError):
            continue
            
    return False


def count_participants(session_id):
   
    query = "SELECT SUM(places) as total FROM participations WHERE session_id = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    conn.close()

    return result['total'] if result['total'] else 0


def get_available_role_spots(session_id, role):

    role = int(role)
    role_limits = {
        1: 4,
        2: 3,
        3: 2
    }
    max_spots = role_limits.get(role, 0)
    
    query = "SELECT SUM(places) as taken FROM participations WHERE session_id = ? AND role = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (session_id, role))
    result = cursor.fetchone()
    conn.close()
    
    taken = result['taken'] if result['taken'] else 0
    return max_spots - taken


def get_most_requested_role_per_session():
    
    query = """
        WITH role_totals AS (
            SELECT session_id, role, SUM(places) as total_places
            FROM participations
            GROUP BY session_id, role
        ),
        ranked_roles AS (
            SELECT session_id, role, total_places,
                   ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY total_places DESC) as rn
            FROM role_totals
        )
        SELECT session_id, role, total_places
        FROM ranked_roles
        WHERE rn = 1
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    role_mapping = {
        1: "Warrior",
        2: "Mage",
        3: "Healer"
    }
    
    result = {} 
    
    for row in rows:
        role_id = row['role']
        result[row['session_id']] = role_mapping.get(role_id, "Unknown")
    
    return result


def count_user_sessions_this_week(user_id):
    
    query = "SELECT COUNT(*) as count FROM participations WHERE user_id = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result['count']


def check_user_time_overlap(user_id, day, time):
    
    query = """
        SELECT COUNT(*) as count 
        FROM participations p
        JOIN sessions s ON p.session_id = s.id
        WHERE p.user_id = ? AND s.day = ? AND s.time = ?
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (user_id, day, time))
    result = cursor.fetchone()
    conn.close()
    return result['count'] > 0


def add_participation(user_id, session_id, role, places):
    
    query = "INSERT INTO participations (user_id, session_id, role, places) VALUES (?, ?, ?, ?)"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (user_id, session_id, role, places))
    conn.commit()
    conn.close()


def get_user_participations(user_id):
    
    query = """
        SELECT p.id as part_id, q.title, s.day, s.time, s.location, p.role, p.places 
        FROM participations p
        JOIN sessions s ON p.session_id = s.id
        JOIN quests q ON s.quest_id = q.id
        WHERE p.user_id = ?
        ORDER BY s.day, s.time
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    participations = cursor.fetchall()
    conn.close()
    return participations


def get_participation_by_id(part_id):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM participations WHERE id = ?", (part_id,))
    part = cursor.fetchone()
    conn.close()
    return part


def delete_participation(part_id):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM participations WHERE id = ?", (part_id,))
    conn.commit()
    conn.close()


def get_master_statistics():
    
    stats = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(places) as total_places FROM participations")
    res = cursor.fetchone()
    stats['total_reserved'] = res['total_places'] if res['total_places'] else 0
    
    conn.close()
    return stats


def get_filtered_sessions(day=None, q_type=None, difficulty=None, role=None):
   
    query = """
        SELECT s.id as session_id, q.id as quest_id, q.title, s.day, s.time, s.location, q.difficulty, q.type 
        FROM sessions s
        JOIN quests q ON s.quest_id = q.id
        WHERE 1=1
    """
    params = []
    
    if day:
        query += " AND s.day = ?"
        params.append(day)
    if q_type:
        query += " AND q.type = ?"
        params.append(q_type)
    if difficulty:
        query += " AND q.difficulty = ?"
        params.append(difficulty)
        
    query += """
        ORDER BY 
            CASE s.day 
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
                WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 
            END, 
            s.time ASC
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    sessions = [dict(row) for row in rows]
    
    if role:
        role = int(role)
        filtered_sessions = []
        for sess in sessions:
            available = get_available_role_spots(sess['session_id'], role)
            if available > 0:
                filtered_sessions.append(sess)
        return filtered_sessions
        
    return sessions


def get_council_sessions():

    query = """
        SELECT s.id as session_id, q.title, s.day, s.time, s.location, q.type, q.difficulty 
        FROM sessions s
        JOIN quests q ON s.quest_id = q.id
        ORDER BY 
            CASE s.day 
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
                WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 
            END, 
            s.time ASC
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    sessions = [dict(row) for row in rows]
    
    for session in sessions:
        sess_id = session["session_id"]
        session["rem_warrior"] = get_available_role_spots(sess_id, 1)
        session["rem_mage"] = get_available_role_spots(sess_id, 2)
        session["rem_healer"] = get_available_role_spots(sess_id, 3)
        session["total_participants"] = count_participants(sess_id)
        
    return sessions


def get_council_statistics():

    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) as c FROM users WHERE priority = 0")
    stats['tot_adventurers'] = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM quests")
    stats['tot_quests'] = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM sessions")
    stats['tot_sessions'] = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) as c FROM participations")
    stats['tot_participations'] = cursor.fetchone()['c']

    cursor.execute("SELECT role, SUM(places) as total_places FROM participations GROUP BY role")
    roles = cursor.fetchall()
    stats['roles'] = {1: 0, 2: 0, 3: 0}
    for r in roles:
        stats['roles'][r['role']] = r['total_places'] if r['total_places'] else 0

    query_type = """
        SELECT q.type, SUM(p.places) as total
        FROM quests q
        JOIN sessions s ON q.id = s.quest_id
        JOIN participations p ON s.id = p.session_id
        GROUP BY q.type
        ORDER BY total DESC LIMIT 1
    """
    cursor.execute(query_type)
    pop_type = cursor.fetchone()
    stats['pop_type'] = pop_type['type'] if pop_type and pop_type['total'] else "No data"

    query_top_sess = """
        SELECT q.title, s.day, s.time, SUM(p.places) as total
        FROM sessions s
        JOIN quests q ON s.quest_id = q.id
        JOIN participations p ON s.id = p.session_id
        GROUP BY s.id
        ORDER BY total DESC LIMIT 1
    """
    cursor.execute(query_top_sess)
    top_sess = cursor.fetchone()
    if top_sess and top_sess['total']:
        stats['top_session'] = f"{top_sess['title']} ({top_sess['day']} {top_sess['time']})"
    else:
        stats['top_session'] = "No data"

    conn.close()
    return stats