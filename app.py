# Python standard libraries
import datetime
import json
import os
import sqlite3
import sys

# Third-party libraries
from flask import Flask, redirect, request, url_for, render_template
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command, get_db, query_db
from user import User

EVENT_TYPES = [
        'soccer',
        'cross country',
        'golf',
        'volleyball',
        'basketball',
        'swimming',
        'bowling',
        'lacrosse',
        'tennis',
        'track and field',
        'trap',
        'theater',
        'music',
        'academic',
        'other'
];

BASE_URL = os.getenv("BASE_URL")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)

try:
    init_db_command()
except sqlite3.OperationalError:
    pass

client = WebApplicationClient(GOOGLE_CLIENT_ID)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def get_google_login_url():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    return client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=f"{BASE_URL}/callback",
        scope=["openid", "email", "profile"],
    )

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

def require_vars(vars):
    for var in vars:
        if not var in request.form:
            raise ValueError("missing var: " + var)

def get_point_totals(db):
    point_totals = query_db(db, """
        select color, count(*) count 
            from points p join users u on (p.users_id = u.users_id)
            group by color
        """, [])

    white_points = 0
    blue_points = 0

    for pt in point_totals:
        print("points: " + str(pt), file=sys.stderr)
        if pt['color'] == 'white':
            white_points = pt['count']
        elif pt['color'] == 'blue':
            blue_points = pt['count']
        else:
            raise ValueError("unknown color: " + pt.color)

    return (white_points, blue_points)

def get_top_10_users(db):
    return query_db(db, """
        select u.name, u.color, u.users_id, count(*) points
            from 
                users u join
                points p on (u.users_id = p.users_id)
            group by u.users_id
            order by count(*) desc
            limit 10
        """, [])

@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(get_google_login_url())

    db = get_db()

    (white_points, blue_points) = get_point_totals(db)

    top_10_users = get_top_10_users(db)

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    point = request.form.get('point', None)

    return render_template(
        'index.html',
        blue_points=blue_points,
        white_points=white_points,
        user=current_user,
        event_types=EVENT_TYPES,
        top_10_users=top_10_users,
        today=today,
        point=point,
    )

@app.route("/point", methods=['POST', 'GET'])
def point():
    if not current_user.is_authenticated:
        return redirect(get_google_login_url())

    require_vars(['event_date', 'event_type', 'event_description'])

    event_date = request.form['event_date']
    event_type = request.form['event_type']
    event_description = request.form['event_description']

    db = get_db()

    if not current_user.color:
        if not 'color' in request.form:
            raise ValueError("missing color value for user " + str(current_user.id))

        color = request.form['color']
        db.execute("update users set color = ? where users_id = ?", [color, current_user.id])

    db.execute("""
        insert into points
            (users_id, event_date, event_type, event_description)
            values (?, ?, ?, ?);
        """,
        [current_user.users_id, event_date, event_type, event_description])
    db.commit()

    return redirect("/?point=1")


@app.route("/login")
def login():
    return redirect(get_google_login_url())

@app.route("/callback")
def callback():
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=f"{BASE_URL}/callback",
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
    else:
        raise ValueError("User email not available or not verified by Google.")

    if not (users_email.endswith('@stmarysschool.org') or
        users_email.endswith('@stmarysmemphis.net')):
        raise ValueError("Google account must be an SMS domain")

    db = get_db()

    user = User.get_by_email(users_email)
    if not user:
        print("create new user", file=sys.stderr)
        User.create(name=users_name, email=users_email)
        user = User.get_by_email(users_email)
    else:
        print("user already exists", file=sys.stderr)

    login_user(user, remember=True)

    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == '__main__':
    app.run()
