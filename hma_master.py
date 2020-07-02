import os, sys, time

import requests as req
import psycopg2

from hma_conf import MASTER_APP, SLAVE_APP, PG_TABLES as TABLES

# You shouldn't need to modify anything here

DB_URL = os.environ['DATABASE_URL']

SLAVE_URL = f"http://{SLAVE_APP}.herokuapp.com"

MASTER_API_URL = f"https://api.heroku.com/apps/{MASTER_APP}"
SLAVE_API_URL = f"https://api.heroku.com/apps/{SLAVE_APP}"

HMA_KEY = os.environ['HMA_SHARED_KEY']

MASTER_TOKEN = os.environ['MASTER_HEROKU_TOKEN']
SLAVE_TOKEN = os.environ['SLAVE_HEROKU_TOKEN']

MASTER_API_HEADERS = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {MASTER_TOKEN}"
        }
SLAVE_API_HEADERS = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {SLAVE_TOKEN}"
        }

API_PAYLOAD_0 = {
        "quantity": 0,
        "size": "free"
        }
API_PAYLOAD_1 = {
        "quantity": 1,
        "size": "free"
        }

#connect to database
conn = psycopg2.connect(DB_URL)

# first, check date and decide what should be done
def main():
    """Checks the date and time, and then decides if a shift from master to slave (or vice versa) is needed. If necessary, makes the shift."""
    date = time.gmtime().tm_mday
    if date == 1 or date == 2: # in case it missed once
        # shift from slave to master, checking to ensure it hasn't already happened
        status = check_status()
        if status == 'slave':
            slave_to_master()
        elif status == 'master':
            print("Shift has probably already happened")
        else:
            print("In a forbidden state:", status)
    elif date == 22 or date == 23: #in case it missed once
        # shift from master to slave, checking to ensure it hasn't already happened
        status = check_status()
        if status == 'master':
            master_to_slave()
        elif status == 'slave':
            print("Shift has probably already happened")
        else:
            print("In a forbidden state:", status)
    else:
        pass


def check_status():
    """
    Check the status of the application, i.e., whether it is running on the master or slave.

    Also check to see if there are any issues, like the web dyno on the slave running, or both workers running etc.
    """
    # assume no web dynos on master - there should never be a web dyno on master
    r = req.get(f"{MASTER_API_URL}/formation/worker", headers=MASTER_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Couldn't get master worker formation")
        print(r.status_code, ":", r.text)
        return 'unknown:1'
    master_worker = r.json()['quantity'] # this is guaranteed to work i think
    r = req.get(f"{SLAVE_API_URL}/formation/worker", headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Couldn't get slave worker formation")
        print(r.status_code, ":", r.text)
        return 'unknown:2'
    slave_worker = r.json()['quantity']
    r = req.get(f"{SLAVE_API_URL}/formation/web", headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Couldn't get slave web formation")
        print(r.status_code, ":", r.text)
        return 'unknown:3'
    slave_web = r.json()['quantity']
    # all done
    if slave_web != 0:
        return 'forbidden-web'
    elif master_worker != 0 and slave_worker != 0:
        return 'both'
    elif master_worker != 0:
        return 'master'
    elif slave_worker != 0:
        return 'slave'
    else:
        return 'none'


def master_to_slave():
    """Shift the process from master to slave, shifting data as needed."""
    print("Shifting from master to slave")
    stop_master_worker()
    setup_slave_web()
    prepare_push()
    push_to_slave()
    stop_slave_web()
    start_slave_worker()
    print("DONE!")


def slave_to_master():
    """Shift the process from slave to master, shifting data as needed."""
    print("Shifting from slave to master")
    stop_slave_worker()
    setup_slave_web()
    pull_from_slave()
    commit_pull_to_db()
    stop_slave_web()
    start_master_worker()
    print("DONE!")


def setup_slave_web():
    """Sets up the web server on the slave, then checks it."""
    print("Starting slave web")
    r = req.patch(f"{SLAVE_API_URL}/formation/web", json=API_PAYLOAD_1, headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to start the web dyno on slave")
        print(r.text)
        return False
    #wait a bit for the web process to start up
    print("Waiting a bit")
    time.sleep(10)
    r = req.get(SLAVE_URL)
    if not r.text.startswith("Index"):
        print("Something is wrong with slave:")
        print(r.text)
        return False

    print("Got response from slave:", r.text)
    return True


# LOTS of code duplication here, should fix sometime
def stop_slave_web():
    """Stops the web process on the slave."""
    print("Stopping slave web")
    r = req.patch(f"{SLAVE_API_URL}/formation/web", json=API_PAYLOAD_0, headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to stop the web dyno on slave")
        print(r.text)
        return False
    #wait a bit for the web process to stop
    print("Waiting a bit")
    time.sleep(2)
    return True



def start_master_worker():
    """Starts the worker process on the master."""
    print("Starting master worker")
    r = req.patch(f"{MASTER_API_URL}/formation/worker", json=API_PAYLOAD_1, headers=MASTER_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to start the worker dyno on master")
        print(r.text)
        return False
    #wait a bit for the worker process to start
    print("Waiting a bit")
    time.sleep(10)
    return True


def stop_master_worker():
    """Stops the worker process on the master."""
    print("Stopping master worker")
    r = req.patch(f"{MASTER_API_URL}/formation/worker", json=API_PAYLOAD_0, headers=MASTER_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to stop the worker dyno on master")
        print(r.text)
        return False
    #wait a bit for the worker process to stop
    print("Waiting a bit")
    time.sleep(2)
    return True


def start_slave_worker():
    """Starts the worker process on the slave."""
    print("Starting slave worker")
    r = req.patch(f"{SLAVE_API_URL}/formation/worker", json=API_PAYLOAD_1, headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to start the worker dyno on slave")
        print(r.text)
        return False
    #wait a bit for the worker process to start up
    print("Waiting a bit")
    time.sleep(10)
    return True



def stop_slave_worker():
    """Stops the worker process on the slave."""
    print("Stopping slave worker")
    r = req.patch(f"{SLAVE_API_URL}/formation/worker", json=API_PAYLOAD_0, headers=SLAVE_API_HEADERS)
    if r.status_code != req.codes.ok:
        print("Unable to stop the worker dyno on slave")
        print(r.text)
        return False
    #wait a bit for the worker process to stop
    print("Waiting a bit")
    time.sleep(2)
    return True


def prepare_push():
    """Prepares to send data from master (this) to slave."""
    print("Preparing to push")
    cur = conn.cursor()
    try:
        for tname in TABLES:
            with open(f'{tname}.db', 'w') as f:
                print(f"Copying {tname}")
                cur.copy_to(f, f'"{tname}"')
        return True
    except IOError:
        print("IO ERROR")
        return False
    finally:
        cur.close()


def push_to_slave():
    """Sends data from the master (this) to the slave."""
    print("Pushing to slave")
    try:
        for tname in TABLES:
            with open(f'{tname}.db', 'rb') as f:
                print(f"Pushing {tname}")
                r = req.post(f"{SLAVE_URL}/push_db/{tname}", files={'file': f}, data={'key': HMA_KEY})
                if r.status_code != req.codes.ok:
                    print("Something wrong with slave on push:")
                    print(r.text)
                    return False
        return True
    except IOError:
        print("IO ERROR")
        return False


def pull_from_slave():
    """Pulls data from the slave."""
    print("Pulling from slave")
    r = req.get(f"{SLAVE_URL}/prepare_pull")
    if r.status_code != req.codes.ok:
        print("Something wrong with slave on prepare pull")
        print(r.text)
        return False
    print("Prepared")
    try:
        for tname in TABLES:
            with open(f'{tname}.db', 'wb') as f:
                print(f"Pulling {tname}")
                r = req.post(f"{SLAVE_URL}/pull_db/{tname}", data={'key': HMA_KEY})
                if r.status_code != req.codes.ok:
                    print("Something went wrong")
                    print(r.text)
                    return False
                f.write(r.content)
        return True
    except IOError:
        print("IO ERROR")
        return False


def commit_pull_to_db():
    """Commit data pulled from slave to the master's database."""
    print("Committing pulled data")
    cur = conn.cursor()
    try:
        for tname in TABLES:
            cur.execute(f"DELETE FROM {tname};")
            with open(f'{tname}.db', 'r') as f:
                print(f"Copying {tname}")
                cur.copy_from(f, f'"{tname}"')
        conn.commit()
        return True
    except IOError:
        print("IO ERROR")
        return False
    finally:
        cur.close()


def debug(mode):
    if mode == 'push':
        master_to_slave()
    elif mode == 'pull':
        slave_to_master()
    elif mode == 'debug':
        print(MASTER_API_HEADERS)
        print(SLAVE_API_HEADERS)
        print(MASTER_API_URL)
        print(SLAVE_API_URL)
    elif mode == 'status':
        print("Current status:", check_status())


if __name__ == '__main__':
    if '--push-to-slave' in sys.argv[1:]:
        debug('pull')
    elif '--pull-from-slave' in sys.argv[1:]:
        debug('push')
    elif '--debug' in sys.argv[1:]:
        debug('debug')
    elif '--status' in sys.argv[1:]:
        debug('status')
    else:
        main()
    #always have to do this
    conn.close()
