__author__ = 'jhroyal'

import json
import logging as log
import sys
import os
import traceback
import re

import requests
import yaml
from flask import Flask
from flask import request

from Poll import PollingMachine


app = Flask(__name__)
env = dict()

@app.route('/', methods=['GET', 'POST'])
def vote_command():
    if request.method == "GET":
        return "The voting machine is up and running"

    token = request.form["token"]
    if env["SLACK_TOKEN"] != token:
        return "Invalid slack token."

    try:
        pm = env["POLLS"]


        requested = request.form["text"]
        user = request.form["user_name"]
        channel = request.form["channel_name"]
        if "help" in requested:
            return "*Help for /poll*\n\n" \
                   "*Start a poll:* `/poll topic \"What's for lunch?\" options sushi --- pizza --- Anything but burgers`\n" \
                   "*End a poll:* /poll stop (The original poll creator must run this"

        if "topic" in requested and "options" in requested:
            print "Creating a new poll"
            topic_match = re.search("topic (.+) options", requested)
            if topic_match:
                topic = topic_match.group(1)
            else:
                return "Malformed Request. Use `/poll help` to find out how to form the request."

            options_match = re.search("options (.*)", requested)
            if options_match:
                options = {x.strip(): 0 for x in options_match.group(1).split("---")}
            else:
                return "Malformed Request. Use `/poll help` to find out how to form the request."
            pm.create_poll(user, channel, topic, options)
            print "PM "+str(pm)
            return "Creating a new poll"
            #
        return "Vote POST request recieved"
    except requests.exceptions.ReadTimeout:
        return "Request timed out :("
    except Exception as e:
        log.error(traceback.format_exc())
        if "SLACK_ERROR_URL" in env and "SLACK_ERROR_CHANNEL" in env:
            send_message_to_admin(env["SLACK_ERROR_URL"], env["SLACK_ERROR_CHANNEL"], user, requested, traceback.format_exc())
        return "Oh no! Something went wrong!"


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
    log.basicConfig(filename='slack-vote.log', level=log.DEBUG, format='%(asctime)s %(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S')
    global env
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "local":
            log.info("Try loading from a local env.yaml file")
            env = yaml.load(file("env.yaml"))
            env["HOST"] = 'localhost'
            env["PORT"] = 5000
        else:
            log.info("Loading environment variables from Bluemix")
            env["SLACK_TOKEN"] = os.getenv("SLACK_TOKEN")
            env["SLACK_ERROR_URL"] = os.getenv("SLACK_ERROR_URL")
            env["SLACK_ERROR_CHANNEL"] = os.getenv("SLACK_ERROR_CHANNEL")
            env["HOST"] = '0.0.0.0'
            env["PORT"] = os.getenv('VCAP_APP_PORT', '5000')

        env["POLLS"] = PollingMachine()
    except Exception as e:
            log.error("Failed to load the environment \n %s" % e)
            sys.exit(2)
    print env
    app.run(host=env["HOST"], port=env["PORT"])
