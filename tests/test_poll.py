from unittest import TestCase
from Poll import Poll

__author__ = 'James Royal'


class TestPoll(TestCase):
    def test_cast_vote_single_vote(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 1

    def test_cast_vote_multiple_votes(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.cast_vote("B", 1)
        assert poll.num_casted_votes == 2
        assert poll.options[0]["count"] == 2

    def test_cast_invalid_vote(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert not poll.cast_vote("A", 3)
        assert poll.num_casted_votes == 0

    def test_cast_invalid_vote_2(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert not poll.cast_vote("A", 0)
        assert poll.num_casted_votes == 0

    def test_cast_vote_multiple_votes_2(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.cast_vote("B", 2)
        assert poll.num_casted_votes == 2
        assert poll.options[0]["count"] == 1
        assert poll.options[1]["count"] == 1

    def test_cast_vote_change_vote(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 1
        assert poll.options[1]["count"] == 0
        assert poll.cast_vote("A", 2)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 0
        assert poll.options[1]["count"] == 1

    def test_cast_same_vote_twice(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 1
        assert poll.options[1]["count"] == 0
        assert poll.cast_vote("A", 2)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 0
        assert poll.options[1]["count"] == 1
        assert poll.cast_vote("A", 2)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 0
        assert poll.options[1]["count"] == 1

    def test_cast_change_vote_twice(self):
        poll = Poll("James", "#jamestestchannel", "Test topic", [{"name": "option1", "count": 0},
                                                                 {"name": "option2", "count": 0}])
        assert poll.cast_vote("A", 1)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 1
        assert poll.options[1]["count"] == 0
        assert poll.cast_vote("A", 2)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 0
        assert poll.options[1]["count"] == 1
        assert poll.cast_vote("A", 1)
        assert poll.num_casted_votes == 1
        assert poll.options[0]["count"] == 1
        assert poll.options[1]["count"] == 0