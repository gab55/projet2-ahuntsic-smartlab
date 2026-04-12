import sys
from datetime import datetime, timezone
from json import JSONDecodeError

import pymysql
import yaml
import os
from src.client_utils import parse_json

# with open('config.yaml', 'r') as file:
#     config = yaml.load(file, Loader=yaml.FullLoader)


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.client_utils as client_utils
import main_utils
config = main_utils.get_config()

test = config['test']
user = config['user']
password = config['password']
host = config['host']
port = config['port']
database = config['database']

schema = main_utils.abs_path("schema.sql", "db")
queries = main_utils.abs_path("queries.sql", "db")
def db_create():
    """
    create database and tables if not exists
    :return: None
    """
    try:
        conn = pymysql.connect(
            user=user,
            password=password,
            host=host,
            port=port
        )
        cursor = conn.cursor()
        with open(schema, 'r') as f:
            create = f.read()
        statements = [stmt.strip() for stmt in create.split(';') if stmt.strip()]

        for stmt in range(len(statements)):
            cursor.execute(statements[stmt])
        conn.commit()
        conn.close()

    except pymysql.Error as e:
        print(e)
        sys.exit(1)


def db_conn():
    """
    Connect to MariaDB database, create it if not exists
    :return: conn, cursor
    """
    try:
        conn = pymysql.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        cursor = conn.cursor()

    except pymysql.Error as e:
        print(e)
        sys.exit(1)
    return conn, cursor

def conn_close(conn):
    """
    close connection
    :param conn:
    :return: Null
    """
    try:
        conn.commit()
        conn.close()
    except pymysql.Error as e:
        print(e)


def insert_event(json_str, topic):
    """

    :param json_str:
    :param topic:
    :return:
    """
    conn, cursor = db_conn()
    if conn is None or cursor is None:
        print("[ERROR] Could not connect to database")
        return

    try:
        query = (f"INSERT INTO events (topic, device, payload, ts_utc)"
                 f"VALUES (%s, %s, %s, %s)")
        cursor.execute(
            query,
            (topic,
             config["device_id"],
             json_str,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
             ),
        )
        conn.commit()
        print(f"[DEBUG] Data inserted into events table: {json_str}")
    except Exception as e:
        print(f"[ERROR] DB error: {e}")



def insert_measurement(json_str, topic):
    """

    :param json_str:
    :param topic:
    :return:
    """
    conn, cursor = db_conn()
    try:
        data = parse_json(json_str)
    except JSONDecodeError:
        query = (f"INSERT INTO telemetry (topic, device, payload, ts_utc)"
                 f"VALUES (%s, %s, %s, %s)")
        cursor.execute(
            query,
            (topic,
            config["device_id"],
            json_str,
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
       )

    if data is not None:
        for key in data:
            if data[key] is None:
                print(f"VALUES ERROR | {key} : {data[key]}")
                return
        insert = (f"INSERT INTO telemetry (topic, device, value, unit, payload, ts_utc)"
                 f"VALUES (%s, %s, %s, %s, %s, %s)")
        cursor.execute(insert, (topic, data['device'], data['value'], data['unit'], json_str, data['ts']))
        #print(f"Data inserted into events table: {data}")
    else:
        print("Invalid JSON string for telemetry")
    conn_close(conn)


def db_query(query=0):
    """
    Execute query and return results
    :param query:
    :return:
    """
    conn, cursor = db_conn()
    with open(queries, 'r') as f:
        sql_content = f.read()

    queries = [query.strip() for query in sql_content.split(';') if query.strip()]

    cursor.execute(queries[query])

    conn_close(conn)





# all_events = queries[0]
# all_measurements = queries[1]
# ten_last_measurements = queries[2]

if __name__ == "__main__":
    db_create()
