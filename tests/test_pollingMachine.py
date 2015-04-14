from unittest import TestCase
from Poll import PollingMachine, Poll

__author__ = 'James Royal'


class TestPollingMachine(TestCase):
    def test_create_poll_no_other_poll(self):
        pm = PollingMachine("abc.com")
        poll = pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        assert isinstance(poll, Poll)
        assert len(pm.active_polls) == 1

    def test_create_poll_existing_different_channel_poll(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        poll = pm.create_poll("James", "#jamestestchannel2", "Test topic", {"option1": 0, "option2": 0})
        assert isinstance(poll, Poll)
        assert len(pm.active_polls) == 2

    def test_create_poll_active_poll_in_channel(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        poll = pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        assert poll is None
        assert len(pm.active_polls) == 1

    def test_create_poll_after_original_poll_closed(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        pm.close_poll("James", "#jamestestchannel")
        poll = pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        assert isinstance(poll, Poll)
        assert len(pm.active_polls) == 1

    def test_close_poll(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        poll = pm.close_poll("James", "#jamestestchannel")
        assert isinstance(poll, Poll)
        assert len(pm.active_polls) == 0

    def test_close_poll_wrong_user(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        poll = pm.close_poll("Lisa", "#jamestestchannel")
        assert isinstance(poll, basestring)
        assert len(pm.active_polls) == 1

    def test_close_poll_no_existing_poll(self):
        pm = PollingMachine("abc.com")
        poll = pm.close_poll("Lisa", "#jamestestchannel")
        assert isinstance(poll, basestring)
        assert len(pm.active_polls) == 0

    def test_vote(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        output = pm.vote("#jamestestchannel", "james", 1)
        assert pm.active_polls["#jamestestchannel"].num_casted_votes == 1
        assert isinstance(output, basestring)

    def test_get_num_of_casted_votes(self):
        pm = PollingMachine("abc.com")
        pm.create_poll("James", "#jamestestchannel", "Test topic", {"option1": 0, "option2": 0})
        output = pm.vote("#jamestestchannel", "james", 1)
        assert pm.get_num_of_casted_votes("#jamestestchannel") == 1