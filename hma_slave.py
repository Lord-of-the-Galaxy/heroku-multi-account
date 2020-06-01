import os, os.path

import psycopg2
from flask import Flask, send_file, request

import hma_conf

# You shouldn't need to modify anything here

app = Flask(__name__)

DB_URL = os.environ['DATABASE_URL']
HMA_KEY = os.environ['HMA_SHARED_KEY']

TABLES = hma_conf.PG_TABLES

conn = psycopg2.connect(DB_URL)

@app.route('/')
def index():
    return f"Index, tables: {TABLES}"

@app.route('/pull_db/<tname>', methods=['GET', 'POST'])
def pull_db(tname):
    if request.method == 'POST' and 'key' in request.form and request.form['key'] == HMA_KEY:
        if tname in TABLES:
            if os.path.isfile(f'{tname}.db'):
                return send_file(f'{tname}.db', as_attachment=True)
            else:
                return "Prepare first", 409
        else:
            return "No such table", 404
    elif request.method == 'POST':
        if 'key' in request.form:
            print("Incorrect key:", request.form['key'])
            return "Incorrect Key!", 403
        else:
            return "Supply shared key!", 403
    else:
        return "Only POST!", 405


@app.route('/prepare_pull')
def prepare_pull():
    cur = conn.cursor()
    try:
        for tname in TABLES:
            with open(f'{tname}.db', 'w') as f:
                print(f"Copying {tname}")
                cur.copy_to(f, f'"{tname}"')
        return "Success"
    except IOError:
        print("IO ERROR")
        return "IO ERROR", 500
    finally:
        cur.close()


@app.route('/push_db/<tname>', methods=['GET', 'POST'])
def push_db(tname):
    if request.method == 'POST' and 'key' in request.form and request.form['key'] == HMA_KEY:
        if tname not in TABLES:
            return "No such table", 404
        if 'file' not in request.files:
            return "Upload a DB file", 400
        f = request.files['file']
        if f.filename == '':
            return "Upload non-empty file", 400
        if f and f.filename == f'{tname}.db':
            print(f"got new DB: {tname}")
            cur = conn.cursor()
            cur.execute(f'DELETE FROM {tname}')
            cur.copy_from(f, f'"{tname}"')
            conn.commit()
            cur.close()
            return "Success!"
        else:
            return "Use correct name", 400
    elif request.method == 'POST':
        if 'key' in request.form:
            print("Incorrect key:", request.form['key'])
            return "Incorrect Key!", 403
        else:
            return "Supply shared key!", 403
    else:
        return "Only POST!", 405


if __name__=='__main__':
    app.run('0.0.0.0', port=8080, debug=True)
