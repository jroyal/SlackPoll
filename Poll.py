from operator import itemgetter
import re
from threading import Timer
import exceptions
import requests

__author__ = 'jhroyal'
import json
from pymongo import MongoClient


def connect_to_mongo():
    """
    Create a connection to the mongodb container

    :return: The slackpoll database object
    """
    try:
        mongodb = MongoClient('pollingdb', 27017)
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
    poll = polls.find_one({"channel": slack_req.form['channel_id']})

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
        'channel': slack_req.form['channel_id'],
        'creator': slack_req.form['user_name'],
        'votes': {},
        'options': options,
        'question': question,
        'vote_count': 0
    }
    polls.insert_one(poll)
    send_poll_start(polls.find_one({"token": token})['url'], poll)
    return "Creating your poll..."


def cast(token, slack_req):
    """
    Cast a vote in a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_id']})

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
        # user has already voted so remove their old vote tallies
        original_vote = poll["votes"][user]
        polls.update_one({"channel": slack_req.form['channel_id']},
                         {"$inc": {"vote_count": -1, "options."+str(original_vote)+".count": -1}})
    polls.update_one({"channel": slack_req.form['channel_id']},
                     {"$inc": {"vote_count": 1, "options."+str(key)+".count": 1},
                      "$set": {"votes."+user: key}})
    return "Vote received. Thank you!"


def count(token, slack_req):
    """
    Get the number of votes cast so far in a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_id']})

    if poll is None:
        return "There is no active poll in this channel currently."
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
    :return: String representing outcome
    """
    db = connect_to_mongo()
    polls = db[token]
    poll = polls.find_one({"channel": slack_req.form['channel_id']})
    if poll is None:
        return "There is no active poll in this channel currently."

    if slack_req.form['user_name'] != poll["creator"]:
        return "Sorry! Only the poll creator can close the poll."

    send_poll_close(polls.find_one({"token": token})['url'], poll)
    delete = polls.delete_one({"channel": slack_req.form['channel_id'], "creator": slack_req.form['user_name']})
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
        "channel": "%s" % poll['channel'],
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
        "channel": "%s" % poll['channel'],
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