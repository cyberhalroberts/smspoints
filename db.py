# http://flask.pocoo.org/docs/1.0/tutorial/database/
import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_raw_db():
    """get db directly, without looking in the flask g first"""
    db = sqlite3.connect("points.db", detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row

    return db

 
def get_db():
    if "db" not in g:
        g.db = get_raw_db()

    return g.db

def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))

def query_db(db, query, params):
  """Returns data from an SQL query as a list of dicts."""
  try:
      things = db.execute(query, params).fetchall()
      unpacked = [{k: item[k] for k in item.keys()} for item in things]
      return unpacked
  except Exception as e:
      print(f"Failed to execute. Query: {query}\n with error:\n{e}")
      return []

@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
