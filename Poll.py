from operator import itemgetter
import re
from threading import Timer
import exceptions
import requests

__author__ = 'jhroyal'
import cloudant
import json
import os
from pymongo import MongoClient


def test_mongo_connection():
    """
    Create a connection to the mongo db container

    Stores it as a global in mongodb
    """
    global mongodb
    print "Testing MONGODB"
    mongodb = MongoClient('mongo-db', 27017)
    db = mongodb.slackpoll
    print db.collection_names()
    print db["tvAMUXMqT0XeGdhgQ86S9eMD"].find_one()


def connect_to_mongo():
    """
    Create a connection to the mongodb container

    :return: The slackpoll database object
    """
    try:
        mongodb = MongoClient('mongo-db', 27017)
    except MongoClient.errors.ConnectionFailure:
        return "Failed to connect to the mongo database!"
    db = mongodb.slackpoll
    return db


def register_slack_account(slack_url, slack_token):
    """
    Register new slack accounts with the polling application

    Adds the new Polling Machine object to the env dict using the token as the key
    :param slack_url: The URL for the incoming web hook for the slack account
    :param slack_token: The token for slash command used by the slack account
    """
    db = connect_to_mongo()
    if slack_token in db.collection_names():
        return "This slack account is already registered."
    data = {'url': slack_url, 'token': slack_token}
    db[slack_token].insert_one(data)
    return "This slack account has been successfully registered."


def validate_token(slack_token):
    """
    Verifies that we know about this token

    :param slack_token: The incoming slack token
    :return: True if we have registered the token, false otherwise
    """
    db = connect_to_mongo()
    if slack_token in db.collection_names():
        return True
    else:
        return False


def create(token, slack_req):
    """
    Create a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :param slack_url: The URL to send the poll too
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_name']})

    if poll is not None:
        return "There is an active poll in this channel already!"

    cmd_txt = slack_req.form['text']
    question_match = re.search("create (.+) options", cmd_txt)
    if question_match:
        question = question_match.group(1)
    else:
        return "Malformed Request. Use `/poll help` to find out how to form the request."

    options_match = re.search("options (.*)", cmd_txt)
    if options_match:
        options = [{"name": x.strip(), "count": 0} for x in options_match.group(1).split("---")]
    else:
        return "Malformed Request. Use `/poll help` to find out how to form the request."

    poll = {
        'channel': slack_req.form['channel_name'],
        'creator': slack_req.form['user_name'],
        'votes': {},
        'options': options,
        'question': question,
        'vote_count': 0
    }
    polls.insert_one(poll)
    send_poll_start(polls.find_one({"token": token})['url'], poll)
    #update_usage_stats(token, slack_req.form['user_name'], slack_req.form['channel_name'])
    return "Creating your poll..."

def update_usage_stats(token, user, channel):
    """
    Update the db that keeps track of usage statistics

    :param token: The token used to represent the slack account
    :param user: The user creating a poll
    :param channel: The channel the poll is being created in
    :return:
    """
    global cloudant_db
    usage_stats = {}
    db = cloudant_db['slackpoll_'+token.lower()]
    doc = db["usage_stats"].get()
    if doc.status_code == 404:
        usage_stats["total_poll_count"] = 1
        usage_stats["channel"] = {channel: 1}
        usage_stats["users"] = {user: 1}
        db["usage_stats"] = usage_stats
    else:
        usage_stats = doc.json()
        usage_stats["total_poll_count"] += 1
        if channel in usage_stats["channel"]:
            usage_stats["channel"][channel] += 1
        else:
            usage_stats["channel"][channel] = 1
        if user in usage_stats["users"]:
            usage_stats["users"][user] += 1
        else:
            usage_stats["users"][user] = 1
        db["usage_stats"].merge(usage_stats)
    return "Working on update_usage_stats"

def cast(token, slack_req):
    """
    Cast a vote in a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_name']})

    if poll is None:
        return "There is no active poll in this channel currently."

    vote = re.search('([0-9]+)', slack_req.form["text"])
    if vote:
        vote = int(vote.group(1))
    else:
        return "Invalid vote. Please use option number."

    key = vote - 1
    if key < 0 or key >= len(poll['options']):
        return "That wasn't a valid voting option!"

    user = slack_req.form["user_name"]
    if user in poll["votes"]:
        original_vote = poll["votes"][user]
        poll['options'][original_vote]["count"] -= 1
        poll["vote_count"] -= 1

    poll["votes"][user] = key
    poll['options'][key]["count"] += 1
    poll["vote_count"] += 1

    doc.merge(poll)
    return "Vote received. Thank you!"


def count(token, slack_req):
    """
    Get the number of votes cast so far in a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :return: String representing outcome
    """
    db = cloudant_db['slackpoll_'+token.lower()]
    doc = db[slack_req.form["channel_name"]]
    doc_resp = doc.get()
    if doc_resp.status_code == 404:
        return "There is no active poll in this channel currently."
    poll = doc_resp.json()
    num_of_votes = poll["vote_count"]

    if num_of_votes:
        return "There have been %s votes cast so far." % num_of_votes
    elif num_of_votes == 0:
        return "Nobody has voted yet :("
    else:
        return "There is no current active poll!"


def close(token, slack_req):
    """
    Close a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :param slack_url: The URL to send the poll too
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_name']})
    if poll is None:
        return "There is no active poll in this channel currently."

    if slack_req.form['user_name'] != poll["creator"]:
        return "Sorry! Only the poll creator can close the poll."

    send_poll_close(polls.find_one({"token": token})['url'], poll)
    delete = polls.delete_one({"channel": slack_req.form['channel_name'], "creator": slack_req.form['user_name']})
    if delete.deleted_count == 0:
        return "Failed to close your poll..."
    return "Closing your poll"


def send_poll_start(url, poll):
    """
    Send the message to slack that alerts users that a poll has been created

    :param url: The url to send the poll too
    :param poll: The json that represents the poll
    :return: None
    """
    payload = {
        "channel": "#%s" % poll['channel'],
        "text": "@%s created a new poll! Vote in it!" % poll['creator'],
        "link_names": 1,
        "attachments": [
            {
                "fallback": "@%s created a new poll! Vote in it!" % poll['creator'],

                "color": "good",
                "mrkdwn_in": ["fields", "text"],
                "fields": [
                    {
                        "title": poll['question'],
                        "value": ""
                    }
                ]
            }
        ]
    }
    for index, option in enumerate(poll['options']):
        payload["attachments"][0]["fields"][0]["value"] += "><%s> %s\n" % (index + 1, option["name"])

    payload["attachments"][0]["fields"][0]["value"] += "\n\nHow do I vote? `/poll cast [option number]`"
    print "Sending an update to slack"
    requests.post(url, data=json.dumps(payload))


def send_poll_close(url, poll):
    """
    Send the message to slack that alerts users that a poll has been closed

    :param url: The url to send the poll too
    :param poll: The json that represents the poll
    :return: None
    """
    payload = {
        "channel": "#%s" % poll['channel'],
        "text": "@%s closed their poll!" % poll['creator'],
        "link_names": 1,
        "attachments": [
            {
                "fallback": "@%s closed their poll!" % poll['creator'],

                "color": "danger",
                "mrkdwn_in": ["fields", "text"],
                "fields": [
                    {
                        "title": poll['question'],
                        "value": ""
                    }
                ]
            }
        ]
    }
    sort = sorted(poll['options'], key=itemgetter('count'), reverse=True)
    for option in sort:
        payload["attachments"][0]["fields"][0]["value"] += ">*%s* received %s votes.\n" % \
                                                           (option["name"], option["count"])

    print "Sending an update to slack"
    requests.post(url, data=json.dumps(payload))