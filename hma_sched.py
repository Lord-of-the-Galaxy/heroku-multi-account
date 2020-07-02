import os
import time

import requests as req

from hma_conf import MASTER_APP

MASTER_API_URL = f"https://api.heroku.com/apps/{MASTER_APP}"

MASTER_TOKEN = os.environ['MASTER_HEROKU_TOKEN']

MASTER_API_HEADERS = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {MASTER_TOKEN}"
        }

API_PAYLOAD = {'command': "python hma_master.py", 'attach':False, 'size': 'free', 'type': 'run', 'time_to_live': 450}

def run_hma():
    r = req.post(f"{MASTER_API_URL}/dynos", json=API_PAYLOAD, headers=MASTER_API_HEADERS)
    if r.status_code != req.codes.created:
        print("Could not start the dyno")
        print(r.text)
        return False
    return True


done = False
while True:
    if time.gmtime().tm_hour == 18:
        if not done:
            done = run_hma()
    else:
        done = False
    time.sleep(900)
