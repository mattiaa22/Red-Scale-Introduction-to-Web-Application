from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User
import users_dao, quests_dao
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "Guerriero_Dragone"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login" 

@app.route("/")
def home():

    day = request.args.get("day")
    q_type = request.args.get("type")
    difficulty = request.args.get("difficulty")
    role = request.args.get("role")
    
    sessions = quests_dao.get_filtered_sessions(day, q_type, difficulty, role)
    
    return render_template(
        "index.html", 
        sessions=sessions,
        current_filters={
            "day": day,
            "type": q_type,
            "difficulty": difficulty,
            "role": role
        }
    )


@app.route("/all_quests")
def all_quests():

    quests = quests_dao.get_all_quests()
    return render_template("quests.html", quests=quests)


@app.route("/profile")
@login_required
def profile():

    if current_user.priority == 1:
        stats = quests_dao.get_master_statistics()
        sessions = quests_dao.get_master_sessions()
        most_requested_roles = quests_dao.get_most_requested_role_per_session()
        
        for session in sessions:
            session_start = get_next_session_datetime(session['day'], session['time'])
            time_diff = session_start - datetime.now()
            session['time_locked'] = time_diff < timedelta(hours=8)

            identificativo = session.get('session_id', session.get('id', 0))
            session['most_requested_role'] = most_requested_roles.get(identificativo, "None yet")
        return render_template("profile.html", stats=stats, sessions=sessions)
    elif current_user.priority == 0:
        participations = quests_dao.get_user_participations(current_user.id)
        return render_template("profile.html", participations=participations)
    else:
        return redirect(url_for("council_dashboard"))
    

@app.route("/quest/<int:quest_id>")
def quest_detail(quest_id):

    quest = quests_dao.get_quest_by_id(quest_id)
    if not quest:
        flash("Quest not found.", "danger")
        return redirect(url_for("all_quests"))
    
    raw_sessions = quests_dao.get_sessions_by_quest(quest_id)
    
    sessions = [dict(row) for row in raw_sessions]

    for session in sessions:
        session_id = session["id"]
        session["rem_warrior"] = quests_dao.get_available_role_spots(session_id, 1)
        session["rem_mage"] = quests_dao.get_available_role_spots(session_id, 2)
        session["rem_healer"] = quests_dao.get_available_role_spots(session_id, 3)
        session["total_participants"] = quests_dao.count_participants(session_id)
        # Check 8 hours
        session_start = get_next_session_datetime(session["day"], session["time"])
        time_diff = session_start - datetime.now()
        session["time_locked"] = time_diff < timedelta(hours=8)

    return render_template("quest.html", quest=quest, sessions=sessions)


def get_next_session_datetime(day_str, time_str):

    weekdays = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 
        'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    now = datetime.now()
    target_weekday = weekdays.get(day_str, 0)
    days_ahead = target_weekday - now.weekday()
    
    if days_ahead < 0:
        days_ahead += 7
        
    #In this way I get hours and minutes from the string HH:MM
    target_hour, target_minute = map(int, time_str.split(':'))
    
    target_datetime = now + timedelta(days=days_ahead)
    target_datetime = target_datetime.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    if days_ahead == 0 and target_datetime < now:
        target_datetime += timedelta(days=7)
        
    return target_datetime

# GCA ROUTES

@app.route("/council")
@login_required
def council_dashboard():

    if current_user.priority != 2:
        flash("Access denied. Guild Council Administrator members only.", "danger")
        return redirect(url_for("home"))
        
    stats = quests_dao.get_council_statistics()
    adventurers = users_dao.get_adventurers_for_council()
    sessions = quests_dao.get_council_sessions()
    
    return render_template("council.html", stats=stats, adventurers=adventurers, sessions=sessions)

# GM ROUTES

@app.route("/master/new_quest", methods=["GET", "POST"])
@login_required
def new_quest():

    if current_user.priority != 1 :
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        title = request.form.get("title")
        duration = int(request.form.get("duration"))
        q_type = request.form.get("type")
        difficulty = request.form.get("difficulty")
        description = request.form.get("description")
        img = ""

        quest_img = request.files["quest_img"]
        if quest_img:
            img = quest_img.filename
            quest_img.save("static/images/" + quest_img.filename)

        quests_dao.create_quest(title, duration, q_type, difficulty, description, img)
        flash("Quest creata con successo!", "success")
        return redirect(url_for("profile"))

    return render_template("newquest.html")


@app.route("/master/new_session", methods=["GET", "POST"])
@login_required
def new_session():

    if current_user.priority != 1:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        quest_id = int(request.form.get("quest_id"))
        day = request.form.get("day")
        time = request.form.get("time")
        location = request.form.get("location")
        
        if quests_dao.check_session_overlap(quest_id, day, time, location):
            flash("Error: the location is booked during this session's hours.", "danger")
            return redirect(url_for("new_session")) 
        
        quests_dao.create_session(quest_id, day, time, location)
        flash("Session scheduled!", "success")
        return redirect(url_for("profile"))
    
    quests = quests_dao.get_all_quests()
    return render_template("newsession.html", quests=quests)


@app.route("/master/edit_session/<int:session_id>", methods=["GET", "POST"])
@login_required
def edit_session(session_id):

    if current_user.priority != 1:
        return redirect(url_for("all_quests"))
    
    session_data = quests_dao.get_session_by_id(session_id)
    if not session_data:
        flash("Session not found.", "danger")
        return redirect(url_for("profile"))
    
    if quests_dao.count_participants(session_id) > 0:
        flash("This session can't be modified, some RS has already joined.", "danger")
        return redirect(url_for("profile"))
 
    session_start = get_next_session_datetime(session_data['day'], session_data['time'])
    if (session_start - datetime.now()) < timedelta(hours=8):
        flash("You cannot edit this session. It starts in less than 8 hours.", "danger")
        return redirect(url_for("profile"))
    
    if request.method == "POST":
        day = request.form.get("day")
        time = request.form.get("time")
        location = request.form.get("location")
        quest_id = session_data['quest_id']
        
        #Overlap check
        if quests_dao.check_session_overlap(quest_id, day, time, location, exclude_session_id=session_id):
            flash("Error: That location is already booked during this session's hours.", "danger")
            return redirect(url_for("edit_session", session_id=session_id))
        
        quests_dao.update_session(session_id, day, time, location)
        flash("Session updated successfully!", "success")
        return redirect(url_for("profile"))
    
    return render_template("editsession.html", session=session_data)


@app.route("/master/delete_session/<int:session_id>")
@login_required
def delete_session(session_id):

    if current_user.priority != 1:
        return redirect(url_for("home"))
        
    session_info = quests_dao.get_session_by_id(session_id)
    if not session_info:
        flash("Session not found.", "danger")
        return redirect(url_for("profile"))
        
    session_start = get_next_session_datetime(session_info['day'], session_info['time'])
    time_diff = session_start - datetime.now()
    
    if time_diff < timedelta(hours=8):
        flash("There are less than 8 hours left until the session starts; you can no longer cancel it!", "danger")
        return redirect(url_for("profile"))
        
    if quests_dao.count_participants(session_id) == 0:
        quests_dao.delete_session(session_id)
        flash("Session deleted successfully.", "success")
    else:
        flash("You cannot cancel a session that already has participants..", "danger")
        
    return redirect(url_for("profile"))

# ADV ROUTES

@app.route("/adventurer/join/<int:session_id>", methods=["POST"])
@login_required
def join_session(session_id):

    if current_user.priority == 2:
        flash("You cannot join the session, only adventurers can do it.", "danger")
        return redirect(url_for("council_dashboard"))  
    if current_user.priority != 0:
        flash("You cannot join the session, only adventurers can do it.", "danger")
        return redirect(url_for("profile"))
    
    role = int(current_user.role)
    if role == 1:
        outrole = "Warrior"
    elif role == 2:
        outrole = "Mage"
    else:
        outrole = "Healer"
    
    places = int(request.form.get("places"))
    quest_id = quests_dao.get_quest_by_session(session_id)

    if places > 2 or places < 1:
        flash("Max bookable places = 2, limit reached.", "danger")
        return redirect(url_for("quest_detail", quest_id=quest_id))
    
    if quests_dao.count_user_sessions_this_week(current_user.id) >= 3:
        flash("Max 3 session for week, limit reached.", "danger")
        return redirect(url_for("profile"))
    
    available = quests_dao.get_available_role_spots(session_id, role)
    if places > available:
        flash(f"There're not other places for {outrole}, limit reached.", "danger")
        return redirect(url_for("quest_detail", quest_id=quest_id))
    
    session_info = quests_dao.get_session_by_id(session_id)
    if quests_dao.check_user_time_overlap(current_user.id, session_info['day'], session_info['time']):
        flash("This session overlaps with another session in which you're already booked.", "danger")
        return redirect(url_for("profile"))

    quests_dao.add_participation(current_user.id, session_id, role, places)
    flash("Registration successfully completed!", "success")
    return redirect(url_for("profile"))


@app.route("/adventurer/cancel_participation/<int:part_id>")
@login_required
def cancel_participation(part_id):

    part_data = quests_dao.get_participation_by_id(part_id)
    
    if part_data and part_data['user_id'] == current_user.id:
        session_info = quests_dao.get_session_by_id(part_data['session_id'])
        
        session_start = get_next_session_datetime(session_info['day'], session_info['time'])
        time_diff = session_start - datetime.now()
        
        if time_diff >= timedelta(hours=8):
            quests_dao.delete_participation(part_id)
            flash("Partecipazione cancellata con successo.", "success")
        else:
            flash("Mancano meno di 8 ore alla sessione, non puoi più cancellarti.", "danger")
    
    return redirect(url_for("profile"))

# Login

@login_manager.user_loader
def load_user(user_id):

    db_user = users_dao.get_user_by_id(user_id)
    if db_user:
        return User(
            id=db_user["id"],
            name=db_user["name"],
            email=db_user["email"],
            password=db_user["password"],
            role=db_user["role"],
            priority=db_user["priority"]
        )
    return None


@app.route("/signup")
def signup():

    return render_template("registration.html")


@app.route("/register", methods=["POST"])
def register():

    priority = 0 #default case --> the new one is an adventurer
    name = request.form.get("name")
    role = request.form.get("role")
    email = request.form.get("email")
    password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256')
    
    if users_dao.get_user_by_email(email):
        flash("Email già in uso.", "danger")
        return redirect(url_for("login"))

    success = users_dao.new_user(name, email, password, role, priority)
        
    if success:
        flash("Got it, you're now a new guild member", "success")
        return redirect(url_for("login"))
    else:
        flash("Internal error: unable to save the user to the database.", "danger")
        return redirect(url_for("signup"))


@app.route("/login")
def login():

    return render_template("login.html")


@app.route("/authenticate", methods=["POST"])
def authenticate():

    email = request.form.get("email")
    password = request.form.get("password")

    db_user = users_dao.get_user_by_email(email)

    if not db_user or not check_password_hash(db_user["password"], password):
        flash("Invalid credentials", "danger")
        return redirect(url_for("login"))
    
    user = User(
        id=db_user["id"],
        name=db_user["name"],
        email=db_user["email"],
        password=db_user["password"],
        role=db_user["role"],
        priority=db_user["priority"]
    )

    login_user(user)
    flash(f"Welcome back RS  {db_user['name']}!", "success")
    return redirect(url_for("home"))


@app.route("/logout")
@login_required
def logout():

    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
