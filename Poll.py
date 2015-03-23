__author__ = 'jhroyal'
import json
import requests
from threading import Timer
from operator import itemgetter


class Poll:
    def __init__(self, user, channel, topic, options):
        self.original_user = user
        self.channel = channel
        self.topic = topic
        self.options = options
        self.option_val_key = []
        self.votes = dict()
        for item in self.options:
            self.option_val_key.append(item)
        self.num_casted_votes = 0
        self.poll_open = True

    def cast_vote(self, user, key):
        print "Cast vote: %s" % key
        if int(key) <= 0 or int(key) > len(self.option_val_key):
            return False

        item = self.option_val_key[int(key) - 1]
        if user in self.votes:
            original_vote = self.votes[user]
            self.options[original_vote] -= 1
            self.num_casted_votes -= 1

        self.votes[user] = item
        self.options[item] += 1
        self.num_casted_votes += 1
        return True

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class PollingMachine():
    def __init__(self, url):
        self.active_polls = dict()
        self.url = url

    def create_poll(self, user, channel, topic, options, timeout=None):
        if channel in self.active_polls:
            return None

        if timeout:
            timeout = int(timeout)
            t = Timer(timeout * 60, self.close_poll, [user, channel])
            t.start()

        poll = Poll(user, channel, topic, options)
        self.active_polls[channel] = poll
        return poll

    def close_poll(self, user, channel):
        if channel in self.active_polls:
            if self.active_polls[channel].original_user != user:
                return "You can not close this poll. Only the original creator can close the poll."
            self.send_poll_close(self.active_polls.pop(channel))
            return "Closing poll..."
        else:
            return "There is no current active poll to close!"

    def vote(self, channel, user, vote):
        if channel in self.active_polls:
            if self.active_polls[channel].cast_vote(user, vote):
                return "Vote received. Thank you!"
            else:
                return "That wasn't a valid voting option!"
        else:
            return "No active poll to vote in!"

    def get_num_of_casted_votes(self, channel):
        if channel in self.active_polls:
            return self.active_polls[channel].num_casted_votes
        else:
            return None

    def __str__(self):
        output = ""
        for poll in self.active_polls:
            output += str(self.active_polls[poll])
        return output

    def send_poll_close(self, poll):
        payload = {
            "channel": poll.channel,
            "text": "@%s closed their poll!" % poll.original_user,
            "link_names": 1,
            "attachments": [
                {
                    "fallback": "@%s closed their poll!" % poll.original_user,

                    "color": "danger",
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
        sort = sorted(poll.options.items(), key=itemgetter(1), reverse=True)
        for option, votes in sort:
            payload["attachments"][0]["fields"][0]["value"] += ">*%s* recieved %s votes.\n" % (option, votes)

        print ("Sending an update to slack")
        requests.post(self.url, data=json.dumps(payload))