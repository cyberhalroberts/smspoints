# Python standard libraries
import csv
import datetime
import io
import json
import os
import sqlite3
import sys

# Third-party libraries
from flask import Flask, redirect, request, url_for, render_template, make_response
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
        'academic',
        'basketball',
        'bowling',
        'cross country',
        'golf',
        'lacrosse',
        'mock trial',
        'music',
        'service',
        'soccer',
        'swimming',
        'tennis',
        'theater',
        'track and field',
        'trap',
        'volleyball',
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
app.config['PERMANENT_SESSION_LIFETIME'] =  datetime.timedelta(minutes=5)

login_manager = LoginManager()
login_manager.init_app(app)

try:
    init_db_command()
except sqlite3.OperationalError:
    pass

if not app.debug:
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
    """raise a ValueError if there is no value for one of the cgi variables named in vars"""
    missing_vars = []
    for var in vars:
        if var not in request.form or request.form[var] == '':
            missing_vars.append(var)

    if len(missing_vars) > 0:
        raise ValueError(f"Missing required data: {', '.join(missing_vars)}")

def get_point_totals(db):
    """ return a list consisting of the white point total and the blue point total """
    point_totals = query_db(db, """
        select p.color, sum(num_points) count from points p group by p.color
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

def get_weekly_top_10_users(db):
    """return the top 10 users by number of points"""
    return query_db(db, """
        select u.name, p.color, u.users_id, sum(p.num_points) points
            from 
                users u join
                points p on (u.users_id = p.users_id)
            group by u.users_id, p.color
            order by sum(p.num_points) desc
            limit 10
        """, [])

def get_top_10_users(db):
    """return the top 10 users by number of points"""
    return query_db(db, """
        select u.name, p.color, u.users_id, sum(p.num_points) points
            from 
                users u join
                points p on (u.users_id = p.users_id)
            group by u.users_id, p.color
            order by sum(p.num_points) desc
            limit 10
        """, [])

def get_latest_points(db):
    """return a list of the latest points by event_date and then created_time"""
    return query_db(db, """
        select u.name, p.color, p.event_date, p.event_type
            from
                users u join
                points p on (u.users_id = p.users_id)
            order by p.event_date desc, p.created_time desc
            limit 20
        """, [])

def need_login():
    if not current_user.is_authenticated:
        return True

    if 'users_id' in request.args:
        return True

    return False

@app.route("/", methods = ['GET'])
def index():
    """main page"""
    if need_login():
        if app.debug:
            dev_login()
        else:
            return redirect(get_google_login_url())

    db = get_db()

    (white_points, blue_points) = get_point_totals(db)

    latest_points = get_latest_points(db)

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    point = request.args.get('point', None)

    message = request.args.get('message', None)

    return render_template(
        'index.html',
        blue_points=blue_points,
        white_points=white_points,
        user=current_user,
        event_types=EVENT_TYPES,
        latest_points=latest_points,
        today=today,
        point=point,
        message=message,
    )

@app.route("/message", methods = ['GET'])
def message():
    """simple message page"""
    m = request.args.get('m', '')

    return render_template(
        'message.html',
        m=m
    )

@app.route("/point", methods=['POST'])
def point():
    """page to add a point"""
    if need_login():
        if app.debug:
            dev_login()
        else:
            return redirect(get_google_login_url())

    require_vars(['event_date', 'event_type', 'event_description', 'num_points'])

    event_date = request.form['event_date']
    event_type = request.form['event_type']
    event_description = request.form['event_description']
    num_points = request.form['num_points']

    db = get_db()

    if not current_user.color:
        if not 'color' in request.form:
            raise ValueError("missing color value for user " + str(current_user.id))

        color = request.form['color']
        db.execute("update users set color = ? where users_id = ?", [color, current_user.id])
        
        current_user.color = color

    u = current_user

    db.execute("""
        insert into points
            (users_id, color, event_date, event_type, event_description, added_by, num_points)
            values (?, ?, ?, ?, ?, ?, ?);
        """,
        [u.users_id, u.color, event_date, event_type, event_description, u.users_id, num_points])
    db.commit()

    return redirect(url_for("index", point=current_user.color))

@app.route("/admin_points", methods=['GET', 'POST'])
def admin_points():
    """display or process admin points page"""
    if need_login():
        if app.debug:
            dev_login()
        else:
            return redirect(get_google_login_url())

    if not current_user.admin and current_user.teacher_points <= 0:
        return redirect(url_for("message", m="admin or teacher points required."))

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if not request.form.get("submit", False):
        return render_template("admin_points.html", today=today, event_types=EVENT_TYPES)

    db = get_db()

    users_id = None
    if email := request.form.get('email', ''):
        if user := User.get_by_email(request.form.get('email', None)):
            users_id = user.users_id
        else:
            message = "Email not found."
            return render_template("admin_points.html", 
                today=today, event_types=EVENT_TYPES, message=message)

    current_id = current_user.users_id

    require_vars(['num_points', 'color', 'event_date', 'event_type', 'event_description'])

    num_points = int(request.form['num_points'])
    color = request.form['color']
    event_date = request.form['event_date']
    event_type = request.form['event_type']
    event_description = request.form['event_description']

    if num_points < user.teacher_points:
        return redirect(url_for("message", m="not enough teacher points."))

    User.update_points(current_id, current_user.teacher_points - num_points)

    db.execute("""
        insert into points
            (users_id, num_points, color, event_date, event_type, event_description, added_by)
            values (?, ?, ?, ?, ?, ?, ?);
        """,
        [users_id, num_points, color, event_date, event_type, event_description, current_id])
    db.commit()

    return redirect(url_for("index", message="Points added!"))

@app.route("/download_points")
def download_points():
    """generate and send a csv of the current points db"""
    if need_login():
        if app.debug:
            dev_login()
        else:
            return redirect(get_google_login_url())

    if not current_user.admin:
        return redirect(url_for("message", m="admin account required."))

    db = get_db()

    points = db.execute("""
        select u.users_id, u.email, u.name, u.color user_color,
                p.color point_color, p.num_points, p.event_date, p.event_type, p.event_description,
                a.email added_by_email, p.created_time
            from points p
                join users a on (p.added_by = a.users_id)
                left join users u on (p.users_id = u.users_id)
            order by
                p.created_time asc
        """)

    fieldnames = ("users_id email name user_color point_color num_points event_date " + 
        "event_type event_description added_by_email created_time").split()

    with io.StringIO() as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow(fieldnames)
        for point in points:
            writer.writerow(point)

        output = make_response(csvfile.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=points.csv"
        output.headers["Content-type"] = "text/csv"

        return output

def dev_login():
    if 'users_id' not in request.args or request.args['users_id'] == '':
        user = User.get_first_admin_user()
    else:
        user = User.get(request.args['users_id'])

    print("login user " + user.name, file=sys.stderr)

    login_user(user, remember=True)

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
        return redirect(url_for("message", m="Google account must belong to SMS"))

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
    app.run(debug=True)
