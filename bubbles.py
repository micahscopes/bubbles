import os
from slackclient import SlackClient
from math import floor, ceil
import time
import datetime
import ago
import re
import shelve
import random
from flask.logging import default_handler
import logging
logger = logging.getLogger()



def BUBBLES_PROMPT(t='', info={}):
    if info.get('size'):
        return f'_*Bubbles of {info.get("size")}! :radio_button: {t}*_'
    elif info.get('quantity'):
        return f'_*{info.get("quantity")} bubbles! :radio_button: {t}*_'
    else:
        return f'_*Bubbles! :radio_button: {t}*_'


BUBBLES_CANCELLED = "These bubbles got popped."

DEFAULT_COUNTDOWN_TIME = 30

try:
    BOT_TOKEN = os.environ['BUBBLES_BOT_TOKEN']
    SC = SlackClient(BOT_TOKEN)
except Exception as e:
    raise Exception(
        "Couldn't authenticate to slack... Please set BUBBLES_BOT_TOKEN in your environment!")

PENDING_BUBBLES_DB = 'pending_bubbles.shelf'

# def get_pending_bubbles(timestamp):
#     db = shelve.open(PENDING_BUBBLES_DB)
#     bubble_prompt = db[timestamp]
#     db.close()
#     return bubble_prompt


def give_help(channel, user, timestamp=None):
    SC.api_call(
        "chat.postMessage",
        channel=channel,
        text=f'<@{user}> Here\'s how to talk to @bubbles:\n ' +
        '''e.g.
 - `@bubbles of 3 in 20 seconds`.
 - `blow 3 @bubbles 10 minutes`.'''
    )


def finish_pending_bubbles(timestamp, channel, message=None):
    db = shelve.open(PENDING_BUBBLES_DB)

    if not timestamp in db:
        db.close()
        return False
    else:
        del db[timestamp]
        db.close()

        SC.api_call(
            "chat.update",
            ts=timestamp,
            channel=channel,
            text=message if message else BUBBLES_CANCELLED
        )

        return True


def queue_pending_bubbles(timestamp):
    db = shelve.open(PENDING_BUBBLES_DB)
    db[timestamp] = True
    db.close()


def bubbles_are_pending(timestamp):
    db = shelve.open(PENDING_BUBBLES_DB)
    result = timestamp in db
    db.close()
    return result


def countdown_precision(countdown):
    if countdown > 30:
        return 1
    else:
        return 2


def countdown_string(t):
    if t > 30 and t < 60:
        s = "in < 1 minute"
    elif t > 15.5 and t <= 30:
        s = "in < 30 seconds"
    elif t <= 0:
        s = "now!"
    else:
        s = ago.human(
            datetime.timedelta(seconds=min(-t, 0)),
            precision=countdown_precision(t),
            future_tense='in ~{}' if t > 30 else 'in < {}'
        )
    return s


def initiate_bubbles(info):
    channel = info['channel']

    started_at = time.time()
    # print("OH")
    countdown_duration = info['countdown']
    if countdown_duration == 0:
        # set a default countdown duration
        countdown_duration = DEFAULT_COUNTDOWN_TIME

    prompt = SC.api_call(
        "chat.postMessage",
        channel=channel,
        text=BUBBLES_PROMPT()
    )

    queue_pending_bubbles(prompt['ts'])

    SC.api_call(
        "reactions.add",
        name="bust_in_silhouette",
        timestamp=prompt['ts'],
        channel=channel
    )

    # print("PROMPT:", str(prompt))
    time_left_now = countdown_duration
    time_left_str = None
    counting_down = True
    while counting_down and time_left_now > -30:
        if not bubbles_are_pending(prompt['ts']):
            return False

        # cache the previous string so we can check if it changed(and prevent rate limiting)
        time_was_left_str = time_left_str
        time_left_str = countdown_string(time_left_now)

        if(time_left_str != time_was_left_str):
            updating_timer_response = SC.api_call(
                "chat.update",
                ts=prompt['ts'],
                channel=channel,
                text=BUBBLES_PROMPT(time_left_str, info)
            )

            # print("remaining time: ", time_left_now)
            # print("time update response", updating_timer_response)
        else:
            # print("string didn't change")
            pass

        time_left_now = ceil(started_at + countdown_duration - time.time())
        snooze_time = 60  # this will change below
        if time_left_now < 30 + snooze_time:
            snooze_time = 10
        if time_left_now < 31:
            snooze_time = 0.25

        time.sleep(snooze_time)
        # print("snoozing for", snooze_time, "seconds")

        if time_left_now < 0:
            # exit the loop
            counting_down = False

    blow_bubbles(info, prompt)

def tabulate_bubbles_for_users(users, size, exclusive, number_of_groups):
    groups = []

    if number_of_groups and not size:
        size = len(users) // number_of_groups

    leftover_users = 0
    try:
        leftover_users = len(users) % size if len(users) > size else 0
    except Exception as e:
        pass

    logger.info("leftover users %i", leftover_users)
    while len(users) >= size:
        group = set()
        size_of_this_group = size
        if leftover_users > 0 and not exclusive:
            # add one of our leftover_user to this group
            size_of_this_group += 1
            leftover_users -= 1
        group = random.sample(users, size_of_this_group)
        users.difference_update(group)
        groups.append(group)
    # print(groups)
    return groups

def blow_bubbles(info, prompt):
    size = info.get('size')
    exclusive = info.get('exclusive')
    number_of_groups = info.get('quantity')
    bot = info['bot']

    emoji_reactions = SC.api_call(
        'reactions.get',
        channel=info['channel'],
        timestamp=prompt['ts'],
        full=True
    )['message']['reactions']

    users = set.union(*[set(e['users']) for e in emoji_reactions])

    try:
        users.remove(bot)
    except Exception as e:
        pass

    logger.info("blowing bubbles for prompt %s", str(info))
    logger.info("with users %s", str(users))

    groups = tabulate_bubbles_for_users(users, size, exclusive, number_of_groups)
    logger.info("and bubbles %s", str(groups))

    group_number = 0
    while len(groups) > 0:
        group = groups.pop()
        if group:
            group_number += 1

        if(info['type'] == 'threaded'):
            bubble = SC.api_call(
                "chat.postMessage",
                channel=info['channel'],
                text=f'bubble # {group_number}... (' + ', '.join(
                    [f'<@{uid}>' for uid in group]) + ')'
            )

            SC.api_call(
                "chat.postMessage",
                thread_ts=bubble['ts'],
                channel=info['channel'],
                text=', '.join(
                    [f'<@{uid}>' for uid in group]) + " :speech_balloon:"
            )
        else:
            bubble = SC.api_call(
                "conversations.open",
                users=",".join(group)
            )
            # print('attempting to open group conversation for',
            #       ",".join(group), 'with bot', bot)
            # print(bubble)
            SC.api_call(
                "chat.postMessage",
                # thread_ts=bubble['ts'],
                channel=bubble['channel']['id'],
                text=', '.join(
                    [f'<@{uid}>' for uid in group]) + " :speech_balloon:"
            )

    finish_pending_bubbles(
        prompt['ts'], prompt['channel'],
        f'{group_number} bubble{" was" if group_number==1 else "s were"} created.'
    )

    return True


QUANTITY = r"(?:(?:(?:blow)|(?:create)|(?:make)|(?:spawn)|(?:prepare)|(?:synthesize)|(?:give\sus)|(?:let\sus\shave))\s(?P<number>\d*))"
SIZE = r"(?:.*?of\s(?P<size>[\d*\s(or)\-]*))"
SECONDS = r"([\d\.\,]+)\s*(?:s(?:ec)*(?:ond)*(?:s)*)"
MINUTES = r"([\d\.\,]+)\s*(?:m(?:in)*(?:utes)*(?:s)*)"
HOURS = r"([\d\.\,]+)\s*(?:h(?:ou)*(?:r)*(?:s)*)"
DM = r"(direct\smessage(?:s)*|dm(?:s)*)"
THREADS = r"(threads|threaded)"
# SECONDS = r"(?:.*?(?:(?:after)|(?:in)*)\s(?P<countdown>\d*\s*(?:(?:min(?:ute)*(?:s)*|(?:sec(?:ond)*(?:s)*)|(?:h(?:ou)*(?:r)*(?:s)*))*)))"
# SECONDS = r"(?:.*?(?:(?:after)|(?:in)*)\s(?P<countdown>\d*\s*(?:(?:min(?:ute)*(?:s)*|(?:sec(?:ond)*(?:s)*)|(?:h(?:ou)*(?:r)*(?:s)*))*)))"
PROMPTS = r"(?:.*\:\n(?P<prompts>.*))"

# basically just extract the info.  if the user decides to use odd grammar, that's on them.


def parse_message(json):
    msg = json['event']['text'].lower()
    info = {
        'channel': json['event']['channel'],
        'bot': json['authed_users'][0],
        'text': json['event']['text'],
        'user': json['event']['user'],
        'msg': msg
    }

    thread_ts = json['event']['thread_ts'] if 'thread_ts' in json['event'] else None
    if thread_ts and (
        "cancel" in msg or
        "stop" in msg or
        "quit" in msg or
        "never mind" in msg or
        "pop" in msg
    ):
        print("CANCELLING", thread_ts)
        info['cancel'] = thread_ts
        return info

    user_intention_count = 0
    try:
        info['quantity'] = int(re.match(QUANTITY, msg)[1])
        user_intention_count += 1
    except Exception as e:
        pass

    try:
        info['seconds'] = float(re.search(SECONDS, msg)[1])
        user_intention_count += 1
    except Exception as e:
        print(e)
        info['seconds'] = 0

    try:
        info['minutes'] = float(re.search(MINUTES, msg)[1])
        user_intention_count += 1
    except Exception as e:
        info['minutes'] = 0

    try:
        info['hours'] = float(re.search(HOURS, msg)[1])
        user_intention_count += 1
    except Exception as e:
        info['hours'] = 0

    try:
        info['prompts'] = re.match(PROMPTS, msg, re.S)[1].split('\n')
        user_intention_count += 1
    except Exception as e:
        pass

    try:
        info['type'] = 'dm' if re.search(DM, msg, re.S)[1] else None
        user_intention_count += 1
    except Exception as e:
        print('error', e)
        info['type'] = None

    try:
        info['type'] = 'threads' if re.search(THREADS, msg, re.S)[1] else 'dm'
        user_intention_count += 1
    except Exception as e:
        info['type'] = 'threads' if not info['type'] else info['type']

    try:
        info['size'] = int(re.match(SIZE, msg)[1])
        user_intention_count += 1
    except Exception as e:
        info['size'] = None if info.get(
            'quantity') or info.get('prompts') else 2

    info['countdown'] = datetime.timedelta(
        minutes=info['minutes'], seconds=info['seconds'], hours=info['hours']).seconds

    if user_intention_count == 0:
        info['help'] = True
    return info
