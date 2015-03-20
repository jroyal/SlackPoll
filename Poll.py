__author__ = 'jhroyal'
import json

class Poll:
    def __init__(self, user, channel, topic, options):
        self.original_user = user
        self.channel = channel
        self.topic = topic
        self.options = options

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class PollingMachine():
    def __init__(self):
        self.active_polls = dict()

    def create_poll(self, user, channel, topic, options):
        self.active_polls[channel] = Poll(user, channel, topic, options)
        print "Created a new poll"

    def __str__(self):
        output = ""
        for poll in self.active_polls:
            output += str(self.active_polls[poll])
        return output