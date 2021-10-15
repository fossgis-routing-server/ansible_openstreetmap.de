#! /usr/bin/env python3

import argparse
import pymysql

parser = argparse.ArgumentParser(description="Check if a table is present in a MariaDB database. This script needs to be run as root and is intended to be called by Ansible roles to check whether a database dump needs to be loaded or not.")
parser.add_argument("database", type=str, help="Database name")
parser.add_argument("table", type=str, help="Table name")
args = parser.parse_args()

if '"' in args.table:
    sys.stderr.write("ERROR: Invalid character \" in table name.\n")
    exit(1)

with pymysql.connect(host='localhost', user='root', unix_socket=True, database=args.database) as conn:
    with conn.cursor() as cursor:
        cursor.execute('SELECT 1 FROM "{}" LIMIT 1'.format(args.table))
        row = cursor.fetchone()
        if row and len(row) == 1 and int(row[0]) == 1:
            sys.stdout.write("table found")
            exit(0)
        else:
            sys.stdout.write("table not found")
            exit(3)
