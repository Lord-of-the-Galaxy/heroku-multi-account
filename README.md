# Heroku Multi-Account hosting
Host an app that requires an always-on worker dyno accross two accounts on heroku.  
**USE AT OWN RISK** - Not really sure if it works, although it probably does.

## Introduction
The two accounts/apps are called `master` and `slave`. The app will end up using almost all the free dyno hours (550) on the master, and just under half the free hours on the slave each month. This means you can use the same account for two slaves. What these scripts do (once configured properly) is to, on the 1st (or rarely 2nd) of each month, copy all the postgresql tables (only the data in the tables, not the tables themselves) from the slave to the master, and turn off the worker dyno on the slave while starting the worker dyno on the master. Then, on the 21st (or 22nd) of every month, do the reverse - copy data from the master to slave, and switch off the worker dyno on the master while turning on the slave.
Overall, this should be able to migrate the app from account to account with minimal disruption and no intervention from the user.
**Note:** you cannot have any web dynos on either the master or the slave for this to work: heroku may make your dynos sleep if there is a web dyno present.

## Usage and Installation
Using this is very simple (hopefully). [Download the lastest release](https://github.com/Lord-of-the-Galaxy/heroku-multi-account/releases). You should find four files in there. First, modify the configuration file, `hma_conf.py` as needed. Next, you can move on to using it on heroku.

### Config vars and Authorization
There are three config variables (alias for environment variables on heroku) for purpose of authentication. They are:  
* `HMA_SHARED_KEY` - Needs to be set on both master and slave, used internally by HMA.  
* `MASTER_HEROKU_TOKEN` - Only needed on master, this is used to make Heroku API requests.  
* `SLAVE_HEROKU_TOKEN` - Only needed on master, this is used to make Heroku API requests.  

#### The HMA Shared Key
This is any alphanumeric-only key that you, the user, needs to generate and set on both the master and slave (using `heroku config:set HMA_SHARED_KEY=<key here>`).

### On the Slave
There's not much setup to do in the slave. You need to add the `hma_conf.py`, `hma_slave.py`, `hma_sched.py` and `wsgi.py` files (to the root of your heroku folder). In your `Procfile`, modify the `worker: <command>` line to `worker: <command> & python hma_sched.py & wait -n`. Next, add (on a new line) `web: gunicorn wsgi:app` to your `Procfile`, and ensure that `flask`, `gunicorn`, `requests` and `psycopg2` are added to the `requirements.txt`. Add the `HMA_SHARED_KEY` and `MASTER_HEROKU_TOKEN` (details on the latter later, it should be same as used on the master) config vars to the app. Now just commit and push your changes (to heroku) and you're almost done. Make sure to scale the dynos to 0 (`heroku ps:scale web=0 worker=0`).
The next step is to provision the postgres addon. **Important:** you need to ensure that all the tables that are to be synced are _already_ created on both the slave and master apps before HMA kicks in. You may have to run the worker once in order to achieve this.
The last step is to create an authorization. Do this using `heroku authorizations:create -d "HMA"`. Note down the `token` it provides, you'll need it again later.

### On the Master
Now you should shift to the master, either by logging out from the slave heroku account (on the CLI) and loggin back in with the master account, or by simply using another (possibly virtual) machine logged into the master account.
On the master, you need to add the `hma_conf.py`, `hma_master.py` and `hma_sched.py` files. Again, in your `Procfile`, modify the `worker: <command>` line to `worker: <command> & python hma_sched.py & wait -n`. Once again, add the `HMA_SHARED_KEY` config var - this needs to be the **exact same** as used on the slave. Make sure `psycopg2` and `requests` are part of the `requirements.txt`. You'll need to push these changes. Provision the `heroku-postgresql` addon like before, ensuring to make any tables needed. Finally, ensure the dynos are scaled to 0 (`heroku ps:scale worker=0`).
The next step is to create another authorization, this time for the master, using the same command. Again, note down the `token`. Now you need to add both the tokens to config vars, using `heroku config:set SLAVE_HEROKU_TOKEN=<token from the slave auth>` and `heroku config:set MASTER_HEROKU_TOKEN=<token from the master auth>`. You're almost done now.
You now only need to set up the [Heroku scheduler](https://devcenter.heroku.com/articles/scheduler). Provision using `heroku addons:create scheduler:standard`, and then run `heroku addons:open scheduler`. Here, [add a scheduled task](https://devcenter.heroku.com/articles/scheduler#scheduling-jobs) to run "Daily" at "00:00" (or whatever time is best for you) with the command `python hma_master.py`.

#### Finishing up
You're all done now, you just need to start the worker dyno on the correct account/app. If the date is between **1st** and **21st** (both inclusive), start the dyno on the _master_ (using `heroku ps:scale worker=1`). Otherwise, start it on the _slave_. This should ensure best results.

## Bugs and features
Please [open an issue](https://github.com/Lord-of-the-Galaxy/heroku-multi-account/issues/new) or pull request (if you fixed it yourself) in case of any bugs or feature requests. Thanks :)
