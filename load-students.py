#!/usr/bin/env python

# Python standard libraries
import csv
import sqlite3
import sys

# Internal imports
from db import get_raw_db, query_db
from user import User

def insert_user(db, user):
    for field in ['email', 'name']:
        if not field in user:
            raise ValueError(f"user {user} missing field {field}")

    if user.get('color', '') not in ['blue', 'white']:
        print(f"skipping user {user['email']} for missing color", file=sys.stderr)
        return

    existing_users = query_db(db, 
        "select * from users where lower(email) = lower(?)", 
        [user['email']])

    if not existing_users:
        db.execute(
            "insert into users (name, email, color) values (?, ?, ?)",
            [user['name'], user['email'], user['color']])
    else:
        db.execute(
            "update users set name = ?, color = ? where lower(email) = lower(?)",
            [user['name'], user['color'], user['email']])


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
