from flask_login import UserMixin

from db import get_db

class User(UserMixin):
    def __init__(self, users_id, name, email, color, admin):
        self.id = users_id
        self.users_id = users_id
        self.name = name
        self.email = email
        self.color = color
        self.admin = admin

    @staticmethod
    def get(users_id):
        db = get_db()
        user = db.execute(
            "SELECT users_id, name, email, color, admin FROM users WHERE users_id = ?", 
            (users_id,)).fetchone()
        if not user:
            return None

        return User(users_id=user[0], name=user[1], email=user[2], color=user[3], admin=user[4])

    @staticmethod
    def get_by_email(email):
        db = get_db()
        user = db.execute(
            "SELECT users_id, name, email, color, admin FROM users WHERE email = ?", 
            (email,)).fetchone()
        if not user:
            return None

        return User(users_id=user[0], name=user[1], email=user[2], color=user[3], admin=user[4])

    @staticmethod
    def create(name, email):
        db = get_db()
        db.execute("INSERT INTO users (name, email) VALUES (?, ?)", 
                (name, email))
        db.commit()
