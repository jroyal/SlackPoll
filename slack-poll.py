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

from Poll import PollingMachine, Poll


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
        log.debug(channel)
        if "help" in requested:
            return "*Help for /poll*\n\n" \
                   "*Start a poll:* `/poll timeout 5 topic What's for lunch? options sushi --- pizza --- Anything but burgers`\n" \
                   "*End a poll:* `/poll close` (The original poll creator must run this\n" \
                   "*Get number of votes:* `/poll count`"

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

            timeout_match = re.search("timeout (\d*)", requested)
            if timeout_match:
                timeout = timeout_match.group(1)
                poll = pm.create_poll(user, channel, topic, options, timeout)
            else:
                poll = pm.create_poll(user, channel, topic, options)

            if poll:
                send_poll_start(env["SLACK_ERROR_URL"], poll)
                log.info(pm)
                return "Creating poll..."
            else:
                return "There is an active poll in this channel already!"

        elif "cast" in requested:
            print "Casting a vote"
            vote = re.search('([0-9]+)', requested)
            if vote:
                vote = vote.group(1)
                return pm.vote(channel, vote)

        elif "count" in requested:
            num = pm.get_num_of_casted_votes(channel)
            if num:
                return "There have been %s votes cast so far." % num
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
        if "SLACK_ERROR_URL" in env and "SLACK_ERROR_CHANNEL" in env:
            send_message_to_admin(env["SLACK_ERROR_URL"], env["SLACK_ERROR_CHANNEL"], user, requested, traceback.format_exc())
        return "Oh no! Something went wrong!"


def send_poll_start(url, poll):
    payload = {
        "channel": poll.channel,
        "text": "%s created a new poll! Vote in it!" % poll.original_user,
        "attachments": [
            {
                "fallback": "%s created a new poll! Vote in it!" % poll.original_user,

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
    for index, option in enumerate(poll.option_val_key):
        payload["attachments"][0]["fields"][0]["value"] += "><%s> %s\n" % (index + 1, option)

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

        env["POLLS"] = PollingMachine(env["SLACK_ERROR_URL"])
    except Exception as e:
            log.error("Failed to load the environment \n %s" % e)
            sys.exit(2)
    print env
    app.run(host=env["HOST"], port=env["PORT"])
