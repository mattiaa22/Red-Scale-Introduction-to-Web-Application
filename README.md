# The Red Scale

A Flask web application for organizing and booking role-playing quest sessions, built with a dark "guild / cult" theme. Adventurers browse quests, join scheduled sessions in their role (Warrior, Mage, or Healer), while Game Masters create quests and manage the weekly schedule.

## Overview

The app has three user types with different permissions:

| Role | Priority level | What they can do |
|---|---|---|
| **Adventurer** | 0 | Browse quests/sessions, filter by day/type/difficulty/role, join a session (as Warrior, Mage or Healer), view and cancel their own participations |
| **Game Master (GM)** | 1 | Create new quests (with image, difficulty, type, description), schedule sessions, edit/cancel sessions (if no one has joined yet), view stats on their quests |
| **Guild Council Administrator (GCA)** | 2 | View guild-wide statistics, browse the full adventurer registry, see all scheduled sessions across every quest |

### Key features

- **Filtering system** on the home page (day, quest type, difficulty, required role)
- **Role-based capacity per session**: max 4 Warrior spots, 3 Mage spots, 2 Healer spots
- **Booking limits**: max 2 places per booking, max 3 sessions per week per adventurer, automatic check for time overlaps with sessions the user already joined
- **Location overlap check**: a Game Master cannot schedule two sessions in the same location at overlapping times
- **8-hour lock rule**: sessions can no longer be edited, cancelled, or un-joined once they start in less than 8 hours
- **Authentication** with hashed passwords (Flask-Login + Werkzeug)

## Tech stack

- **Backend:** Python, Flask, Flask-Login
- **Database:** SQLite3 (`guild.db`)
- **Templating:** Jinja2
- **Frontend:** Bootstrap 5, Bootstrap Icons, custom CSS
- **Security:** password hashing via `werkzeug.security` (pbkdf2:sha256)

## Project structure

```
├── app.py              # Routes and application logic
├── models.py            # User model (Flask-Login UserMixin)
├── users_dao.py         # Database access layer — users
├── quests_dao.py        # Database access layer — quests, sessions, participations
├── templates/
│   ├── base.html         # Shared layout, navbar, flash messages
│   ├── index.html        # Home / quest board with filters
│   ├── quests.html        # Full quest archive
│   ├── quest.html         # Single quest detail + session list
│   ├── profile.html       # Profile view (different per role)
│   ├── council.html       # Guild Council dashboard
│   ├── newquest.html      # GM: create a new quest
│   ├── newsession.html    # GM: schedule a session
│   ├── editsession.html   # GM: edit a session
│   ├── login.html
│   └── registration.html
└── static/
    ├── styles/, js/, images/
```

## Getting started

1. **Clone the repository**
   ```bash
   git clone https://github.com/mattiaa22/Red-Scale-Introduction-to-Web-Application.git
   cd Red-Scale-Introduction-to-Web-Application
   ```

2. **Install the dependencies**
   ```bash
   pip install flask flask-login werkzeug
   ```

3. **Make sure the database exists** (`guild.db` in the project root) with the tables `users`, `quests`, `sessions`, and `participations`.

4. **Run the app**
   ```bash
   python app.py
   ```
   The app will be available at `http://127.0.0.1:5000/`.

## Test accounts

You can try out the different roles using the demo accounts below (run the app locally as described above):

| Role | Email | Password |
|---|---|---|
| Guild Council Administrator | `council@email.it` | `council123` |
| Game Master | `master@email.it` | `master123` |
| Adventurer — Warrior | `baraza@email.it` | `baraza123` |
| Adventurer — Warrior | `kazek@email.it` | `kazek123` |
| Adventurer — Mage | `velytra@email.it` | `velytra123` |
| Adventurer — Mage | `kahel@email.it` | `kahel123` |
| Adventurer — Healer | `zyriel@email.it` | `zyriel123` |
| Adventurer — Healer | `aethor@email.it` | `aethor123` |

> ⚠️ These are demo/test accounts for evaluation purposes only — not real user data.

### Suggested test flow

1. Log in as **Game Master** (`master@email.it`) → create a new quest → schedule a session for it.
2. Log in as an **Adventurer** (e.g. `baraza@email.it`, Warrior) → join that session from the quest page.
3. Log in as the **Guild Council Administrator** (`council@email.it`) → check the dashboard to see the updated stats and the new participation.

## Author

Mattia Arpaia — project developed for the *Introduction to Web Application Development* course exam.
