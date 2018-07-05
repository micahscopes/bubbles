import pytest
import os
from slackclient import SlackClient
import pdb
import bubbles
from tests.test_fake_slack import fake_user_message

# a few example tests

def test_minutes():
    message = fake_user_message("@bubbles in 3 minutes")
    assert bubbles.understand_message(message).get('minutes') == 3

def test_group_size():
    message = fake_user_message("@bubbles of 5")
    assert bubbles.understand_message(message).get('size') == 5

def test_group_tabulation():
    message = fake_user_message("@bubbles of 2 in 10s")
    size = bubbles.understand_message(message).get('size')
    users = ['a','b','c','d','e','f','g']
    groups = bubbles.tabulate_bubbles_for_users(users, size)
    print(groups)

    assert True


def test_small_talk():
    message = fake_user_message("hello @bubbles")
    assert bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("Hi @bubbles")
    assert bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("good morning, @bubbles")
    assert bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("good afternoon, @bubbles")
    assert bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("@bubbles, Shut up!")
    assert bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("@bubbles of 2 in 10s")
    assert not bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("@bubbles of 5")
    assert not bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("@bubbles in 3 minutes")
    assert not bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("Help @bubbles")
    assert not bubbles.understand_message(message).get('small_talk')

    message = fake_user_message("@bubbles how")
    assert not bubbles.understand_message(message).get('small_talk')

