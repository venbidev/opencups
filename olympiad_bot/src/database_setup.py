#!/usr/bin/env python3
import sqlite3

DATABASE_NAME = "olympiad_bot/olympiad_portal.db"

def create_connection():
    """ create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        print(f"SQLite version: {sqlite3.sqlite_version}")
        print(f"Successfully connected to database {DATABASE_NAME}")
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def main():
    sql_create_olympiads_table = """
    CREATE TABLE IF NOT EXISTS Olympiads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL, -- YYYY-MM-DD
        subject TEXT,
        description TEXT
    );
    """

    sql_create_users_table = """
    CREATE TABLE IF NOT EXISTS Users (
        telegram_id INTEGER PRIMARY KEY,
        snils TEXT UNIQUE,
        is_admin BOOLEAN DEFAULT 0
    );
    """

    sql_create_results_table = """
    CREATE TABLE IF NOT EXISTS Results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        olympiad_id INTEGER NOT NULL,
        user_snils TEXT NOT NULL,
        full_name TEXT NOT NULL,
        score INTEGER,
        place INTEGER,
        diploma_link TEXT,
        FOREIGN KEY (olympiad_id) REFERENCES Olympiads (id)
    );
    """

    # create a database connection
    conn = create_connection()

    # create tables
    if conn is not None:
        create_table(conn, sql_create_olympiads_table)
        print("Olympiads table created (or already exists).")
        create_table(conn, sql_create_users_table)
        print("Users table created (or already exists).")
        create_table(conn, sql_create_results_table)
        print("Results table created (or already exists).")
        conn.close()
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    main()

