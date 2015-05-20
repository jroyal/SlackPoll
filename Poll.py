from operator import itemgetter
import re
import requests

__author__ = 'jhroyal'
import cloudant
import json
import os


def connect_to_cloudant():
    """
    Create a connection to the cloudant db service

    Stores it as a global in cloudant_db
    """
    global cloudant_db
    cloudant_info_json = json.loads(os.getenv("VCAP_SERVICES"))
    credentials = cloudant_info_json["cloudantNoSQLDB"][0]["credentials"]
    cloudant_db = cloudant.Account(credentials["username"])

    login = cloudant_db.login(credentials["username"], credentials["password"])
    if login.status_code != 200:
        return "Failed to connect to the cloudant."
    return "Connected to cloudant successfully!"


def register_slack_account(slack_url, slack_token):
    """
    Register new slack accounts with the polling application

    Adds the new Polling Machine object to the env dict using the token as the key
    :param slack_url: The URL for the incoming web hook for the slack account
    :param slack_token: The token for slash command used by the slack account
    """
    global cloudant_db
    db = cloudant_db.database("slackpoll_"+slack_token.lower())
    resp = db.put()
    if resp.status_code == 412:
        return "This slack account is already registered."
    elif resp.status_code == 201:
        data = {'url': slack_url, 'token': slack_token}
        db['account_info'] = data
        return "This slack account has been successfully registered."
    else:
        return "Registration failed."


def load_tokens():
    """
    Collects all of the data needed to connect to the slack accounts
    registered with this slack poll

    :returns dictionary where key = token; val = account data
    """
    global cloudant_db
    tokens = {}
    for db_name in cloudant_db.all_dbs().json():
        if "slackpoll" in db_name:
            db = cloudant_db[db_name]
            account_info = db["account_info"].get().json()
            tokens[account_info["token"]] = account_info
    return tokens


def create(token, slack_req, slack_url):
    """
    Create a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :param slack_url: The URL to send the poll too
    :return: String representing outcome
    """
    global cloudant_db
    db = cloudant_db['slackpoll_'+token.lower()]
    doc = db[slack_req.form["channel_name"]].get()
    if doc.status_code == 200:
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

    timeout_match = re.search("timeout (\d*)", cmd_txt)
    if timeout_match:
        timeout = timeout_match.group(1)

    poll = {
        'channel': slack_req.form['channel_name'],
        'creator': slack_req.form['user_name'],
        'votes': {},
        'options': options,
        'question': question,
        'vote_count': 0
    }
    db[slack_req.form["channel_name"]] = poll
    send_poll_start(slack_url, poll)
    return "Creating your poll..."


def cast(token, slack_req):
    """
    Cast a vote in a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :return: String representing outcome
    """
    global cloudant_db
    vote = re.search('([0-9]+)', slack_req.form["text"])
    if vote:
        vote = int(vote.group(1))

    db = cloudant_db['slackpoll_'+token.lower()]
    doc = db[slack_req.form["channel_name"]]
    doc_resp = doc.get()
    if doc_resp.status_code == 404:
        return "There is no active poll in this channel currently."
    poll = doc_resp.json()

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


def close(token, slack_req, slack_url):
    """
    Close a poll

    :param token: The token used to represent the slack account
    :param slack_req: The request object from slack
    :param slack_url: The URL to send the poll too
    :return: String representing outcome
    """
    global cloudant_db
    db = cloudant_db['slackpoll_'+token.lower()]
    doc = db[slack_req.form["channel_name"]]
    doc_resp = doc.get()
    if doc_resp.status_code == 404:
        return "There is no active poll in this channel currently."
    poll = doc_resp.json()

    if slack_req.form['user_name'] != poll["creator"]:
        return "Sorry! Only the poll creator can close the poll."

    send_poll_close(slack_url, poll)
    doc.delete(poll['_rev']).raise_for_status()
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