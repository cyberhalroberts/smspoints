from flask_login import UserMixin

from db import get_db

class User(UserMixin):
    def __init__(self, users_id, name, email, color, admin, teacher_points):
        self.id = int(users_id)
        self.users_id = int(users_id)
        self.name = name
        self.email = email
        self.color = color
        self.admin = bool(admin)
        self.teacher_points = int(teacher_points)

    def _make_user(u):
        return User(users_id=u[0], name=u[1], email=u[2], color=u[3], admin=u[4], teacher_points=u[5])

    @staticmethod
    def get(users_id):
        db = get_db()
        user = db.execute(
            "SELECT users_id, name, email, color, admin, teacher_points FROM users WHERE users_id = ?", 
            (users_id,)).fetchone()
        if not user:
            return None

        return User._make_user(user)


    @staticmethod
    def get_first_admin_user():
        db = get_db();
        id = db.execute("select min(users_id) from users where admin").fetchone()
        if not id:
            return None

        return User.get(id[0])

    @staticmethod
    def get_by_email(email):
        db = get_db()
        user = db.execute(
            "SELECT users_id, name, email, color, admin, teacher_points FROM users WHERE email = ?", 
            (email,)).fetchone()
        if not user:
            return None

        return User._make_user(user)

    def update_points(users_id, points):
        db = get_db()
        db.execute("UPDATE users SET teacher_points = ? where users_id = ?", (points, users_id))
        db.commit()

    @staticmethod
    def create(name, email):
        db = get_db()
        db.execute("INSERT INTO users (name, email) VALUES (?, ?)", 
                (name, email))
        db.commit()
