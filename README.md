# Heroku Multi-Account hosting
Host an app that requires an always-on worker dyno accross two accounts on heroku.

## Introduction
The two accounts are called `master` and `slave`. The app will end up using almost all the free dyno hours (550) on the master, and just under half the free hours on the slave each month. This means you can use the same account for two slaves. What these scripts do (once configured properly) is to, on the 1st (or rarely 2nd) of each month, copy all the postgresql tables (only the data in the tables, not the tables themselves) from the slave to the master, and turn off the worker dyno on the slave while starting the worker dyno on the master. Then, on the 21st (or 22nd) of every month, do the reverse - copy data from the master to slave, and switch off the worker dyno on the master while turning on the slave.
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

### On the Master
