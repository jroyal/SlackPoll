__author__ = 'jhroyal'

import sys
import os
import traceback
import requests
from flask import Flask
from flask import request

import poll



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
        result = poll.register_slack_account(slack_url, slack_token)
        env.update(poll.load_tokens())
        return result

    if token not in env:
        return "This Slack Account hasn't been registered with the polling application.\n" \
               "Please run `/poll register [incoming webhook url] [slash command token]`"

    try:
        requested = request.form["text"]
        if "help" in requested:
            return "*Help for /poll*\n\n" \
                   "*Start a poll:* `/poll create What's for lunch? options sushi --- pizza --- Anything but burgers`\n" \
                   "*End a poll:* `/poll close` (The original poll creator must run this)\n" \
                   "*Cast a Vote:* `/poll cast [option number]`\n" \
                   "*Get number of votes cast so far:* `/poll count`"

        if "create" in requested and "options" in requested:
            print "Creating a new poll"
            return poll.create(token, request, env[token]["url"])

        elif "cast" in requested:
            print "Casting a vote"
            return poll.cast(token, request)

        elif "count" in requested:
            print "Getting vote count"
            return poll.count(token, request)

        elif "close" in requested:
            print "Closing a poll"
            return poll.close(token, request, env[token]["url"])

        else:
            return "Unknown request recieved"
    except requests.exceptions.ReadTimeout:
        return "Request timed out :("
    except Exception as e:
        print traceback.format_exc()
        return "Oh no! Something went wrong!"


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
    poll.connect_to_cloudant()
    env.update(poll.load_tokens())
    app.run(host=env["HOST"], port=env["PORT"])
