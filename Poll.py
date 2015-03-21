__author__ = 'jhroyal'
import json


class Poll:
    def __init__(self, user, channel, topic, options):
        self.original_user = user
        self.channel = channel
        self.topic = topic
        self.options = options
        self.option_val_key = []
        for item in self.options:
            self.option_val_key.append(item)
        self.num_casted_votes = 0
        self.poll_open = True

    def cast_vote(self, key):
        key = int(key)
        print "Cast vote: %s" % key
        if key <= 0 or key > len(self.option_val_key):
            return False

        item = self.option_val_key[int(key) - 1]
        self.options[item] += 1
        self.num_casted_votes += 1
        return True

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class PollingMachine():
    def __init__(self):
        self.active_polls = dict()

    def create_poll(self, user, channel, topic, options):
        poll = Poll(user, channel, topic, options)
        self.active_polls[channel] = poll
        return poll

    def close_poll(self, channel):
        if channel in self.active_polls:
            return self.active_polls.pop(channel)
        else:
            return "There is no current active poll to close!"

    def vote(self, channel, vote):
        if channel in self.active_polls:
            if self.active_polls[channel].cast_vote(vote):
                return "Vote received. Thank you!"
            else:
                return "That wasn't a valid voting option!"
        else:
            return "No active poll to vote in!"

    def get_num_of_casted_votes(self, channel):
        if channel in self.active_polls:
            return self.active_polls[channel].num_casted_votes
        else:
            return "There is no current active poll!"

    def __str__(self):
        output = ""
        for poll in self.active_polls:
            output += str(self.active_polls[poll])
        return output