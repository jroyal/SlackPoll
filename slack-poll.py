__author__ = 'jhroyal'

import json
import logging as log
import sys
import os
import traceback
import re
import cloudant
import requests
import yaml
from flask import Flask
from flask import request

from Poll import PollingMachine, Poll


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def vote_command():
    if request.method == "GET":
        return "The voting machine is up and running"

    token = request.form["token"]
    requested = request.form["text"]

    if "register" in requested:
        if token in env:
            return "This slack account has already been registered by this application."
        command = requested.split(" ")
        slack_url = command[1]
        slack_token = command[2]
        return register(slack_url, slack_token)

    if token not in env:
        return "This Slack Account hasn't been registered with the polling application.\n" \
               "Please run `/poll register [incoming webhook url] [slash command token]`"

    try:
        pm = env[token]

        requested = request.form["text"]
        user = request.form["user_name"]
        if "channel_id" in request.form:
            channel = request.form["channel_id"]
        else:
            channel = request.form["channel_name"]
        log.debug(channel)
        if "help" in requested:
            return "*Help for /poll*\n\n" \
                   "*Start a poll:* `/poll timeout 5 topic What's for lunch? options sushi --- pizza --- Anything but burgers`\n" \
                   "*End a poll:* `/poll close` (The original poll creator must run this)\n" \
                   "*Cast a Vote:* `/poll cast [option number]`\n" \
                   "*Get number of votes:* `/poll count`"

        if "topic" in requested and "options" in requested:
            log.info("Creating a new poll")
            topic_match = re.search("topic (.+) options", requested)
            if topic_match:
                topic = topic_match.group(1)
            else:
                return "Malformed Request. Use `/poll help` to find out how to form the request."

            options_match = re.search("options (.*)", requested)
            if options_match:
                options = [{"name": x.strip(), "count": 0} for x in options_match.group(1).split("---")]
            else:
                return "Malformed Request. Use `/poll help` to find out how to form the request."

            timeout_match = re.search("timeout (\d*)", requested)
            if timeout_match:
                timeout = timeout_match.group(1)
                poll = pm.create_poll(user, channel, topic, options, timeout)
            else:
                poll = pm.create_poll(user, channel, topic, options)

            if poll:
                send_poll_start(pm.url, poll)
                log.info(pm)
                return "Creating poll..."
            else:
                return "There is an active poll in this channel already!"

        elif "cast" in requested:
            log.info("Casting a vote")
            vote = re.search('([0-9]+)', requested)
            if vote:
                vote = vote.group(1)
                return pm.vote(channel, user, vote)

        elif "count" in requested:
            num = pm.get_num_of_casted_votes(channel)
            if num:
                return "There have been %s votes cast so far." % num
            elif num == 0:
                return "Nobody has voted yet :("
            else:
                return "There is no current active poll!"

        elif "close" in requested:
            output = pm.close_poll(user, channel)
            return output

        else:
            return "Unknown request recieved"
    except requests.exceptions.ReadTimeout:
        return "Request timed out :("
    except Exception as e:
        log.error(traceback.format_exc())
        if "SLACK_ERROR_CHANNEL" in env:
            send_message_to_admin(pm.url, env["SLACK_ERROR_CHANNEL"], user, requested, traceback.format_exc())
        return "Oh no! Something went wrong!"


def register(slack_url, slack_token):
    """
    Register new slack accounts with the polling application

    Adds the new Polling Machine object to the env dict using the token as the key
    :param slack_url: The URL for the incoming web hook for the slack account
    :param slack_token: The token for slash command used by the slack account
    """
    global cloudant_db
    global env
    db = cloudant_db.database("slackpoll_"+slack_token.lower())
    resp = db.put()
    if resp.status_code == 412:
        return "This slack account is already registered."
    elif resp.status_code == 201:
        data = {'url': slack_url, 'token': slack_token}
        db['account_info'] = data
        env[slack_token] = data
        return "This slack account has been successfully registered."
    else:
        return "Registration failed."



def load_tokens():
    global cloudant_db
    global env
    for db_name in cloudant_db.all_dbs().json():
        if "slackpoll" in db_name:
            db = cloudant_db[db_name]
            account_info = db["account_info"].get().json()
            env[account_info["token"]] = account_info


def connect_to_cloudant():
    """
    Create a connection to the cloudant db service

    Stores it as a global in cloudant_db
    :return:
    """
    global cloudant_db
    cloudant_info_json = json.loads(os.getenv("VCAP_SERVICES"))
    credentials = cloudant_info_json["cloudantNoSQLDB"][0]["credentials"]
    cloudant_db = cloudant.Account(credentials["username"])

    login = cloudant_db.login(credentials["username"], credentials["password"])
    if login.status_code != 200:
        return "Failed to connect to the Cloudant DB"



def test():
    global cloudant_db
    db = cloudant_db.database("test")
    result = db.put()
    doc = db['account_info'].get().json()
    db['account_info'].merge({'url': 'facebook.com'})
    #db['account_info'] = {'url': 'facebook.com', "_rev": rev}
    for doc in db.all_docs():
        print doc
    print db['account_info'].get().json()



def send_poll_start(url, poll):
    payload = {
        "channel": poll.channel,
        "text": "@%s created a new poll! Vote in it!" % poll.original_user,
        "link_names": 1,
        "attachments": [
            {
                "fallback": "@%s created a new poll! Vote in it!" % poll.original_user,

                "color": "good",
                "mrkdwn_in": ["fields", "text"],
                "fields": [
                    {
                        "title": poll.topic,
                        "value": ""
                    }
                ]
            }
        ]
    }
    for index, option in enumerate(poll.options):
        payload["attachments"][0]["fields"][0]["value"] += "><%s> %s\n" % (index + 1, option["name"])

    payload["attachments"][0]["fields"][0]["value"] += "\n\nHow do I vote? `/poll cast [option number]`"
    log.info("Sending an update to slack")
    requests.post(url, data=json.dumps(payload))


def send_message_to_admin(url, channel, user, call, stacktrace):
    payload = {
        "channel": channel,
        "text": "There was an ERROR!!",
        "attachments": [
            {
                "fallback": "There was an error; check the log",
                "color": "danger",
                "fields": [
                    {
                        "title": "Here is some more information",
                        "value": "User: %s\n"
                                 "Command: %s\n"
                                 "%s" % (user, call, stacktrace),
                        "short": False
                    }
                ]
            }
        ]
    }
    log.info("Sending an update to slack")
    requests.post(url, data=json.dumps(payload))

if __name__ == "__main__":
    global env
    env = dict()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "local":
            env["HOST"] = 'localhost'
            env["PORT"] = 5000
        else:
            env["HOST"] = '0.0.0.0'
            env["PORT"] = os.getenv('VCAP_APP_PORT', '5000')
    except Exception as e:
            print "Failed to load the environment \n %s" % e
            sys.exit(2)
    connect_to_cloudant()
    load_tokens()
    print env
    app.run(host=env["HOST"], port=env["PORT"])
