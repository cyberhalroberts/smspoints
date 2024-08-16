#!/usr/bin/env python

# Python standard libraries
import csv
import sqlite3
import sys

# Internal imports
from db import get_raw_db, query_db
from user import User

# number of points to give to each teacher
STARTING_TEACHER_POINTS = 50

def insert_user(db, user):
    for field in ['email', 'name']:
        if not field in user:
            raise ValueError(f"user {user} missing field {field}")

    if user.get('color', '') not in ['blue', 'white']:
        print(f"skipping user {user['email']} for missing color", file=sys.stderr)
        return

    user['color'] = user['color'].lower()
    user['email'] = user['email'].lower()
    user['teacher'] = user.get('teacher', 0);

    existing_users = query_db(db, 
        "select * from users where lower(email) = lower(?)", 
        [user['email']])

    if not existing_users:
        db.execute(
            "insert into users (name, email, color, teacher) values (?, ?, ?, ?)",
            [user['name'], user['email'], user['color'], user['teacher']])
        existing_users = query_db(db, 
            "select * from users where lower(email) = lower(?)", 
            [user['email']])
    else:
        print(f"skipping user {user['email']} already exists", file=sys.stderr)


    if user['teacher']:
        users_id = existing_users[0]['users_id']
        pool = query_db(db,
            "select * from point_pools where users_id = ?",
            [users_id])
        if not pool:
            db.execute(
                "insert into point_pools(users_id, points) values (?, ?)",
                [users_id, STARTING_TEACHER_POINTS]);

def main():
    db = get_raw_db()

    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <csv file>", file=sys.stderr)
        return

    csv_file = sys.argv[1]

    users = []
    with open(csv_file, 'r') as data:
        for user in csv.DictReader(data):
            print(f"inserting {user['email']}", file=sys.stderr)
            insert_user(db, user)

    db.commit()


main()
