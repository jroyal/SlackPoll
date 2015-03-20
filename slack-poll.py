__author__ = 'jhroyal'

import json
import requests
import yaml
import logging as log
import sys
import os
from flask import Flask
from flask import request
import traceback


app = Flask(__name__)
env = dict()

@app.route('/', methods=['GET', 'POST'])
def vote_command():
    if request.method == "GET":
        return "The voting machine is up and running"
    requested = request.form["text"]
    user = request.form["user_name"]
    token = request.form["token"]
    if env["SLACK_TOKEN"] != token:
        return "Invalid slack token."
    try:
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

    except Exception as e:
            log.error("Failed to load the environment \n %s" % e)
            sys.exit(2)
    print env
    app.run(host=env["HOST"], port=env["PORT"])
