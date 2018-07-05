import os
import warnings
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

def BUBBLES_PROMPT(t='', context={}):
    if context.get('size'):
        return f'_*Bubbles of {context.get("size")}! :radio_button: {t}*_'
    elif context.get('quantity'):
        return f'_*{context.get("quantity")} bubbles! :radio_button: {t}*_'
    else:
        return f'_*Bubbles! :radio_button: {t}*_'


BUBBLES_CANCELLED = "These bubbles got popped."

DEFAULT_COUNTDOWN_TIME = 30

try:
    BOT_TOKEN = os.environ['BUBBLES_BOT_TOKEN']
    SC = SlackClient(BOT_TOKEN)
except Exception as e:
    warnings.warn(
        "Couldn't authenticate to slack... Please set BUBBLES_BOT_TOKEN in your environment!")

PENDING_BUBBLES_DB = 'pending_bubbles.shelf'
BUBBLES_STATS_DB = 'bubbles_stats.shelf'

def give_help(channel, user, timestamp=None):
    SC.api_call(
        "chat.postMessage",
        channel=channel,
        text=f'<@{user}> Here\'s how to talk to @bubbles:\n ' +
        '''e.g.
 - `@bubbles of 3 in 20 seconds`.
 - `blow 3 @bubbles 10 minutes`.'''
    )


def small_talk(channel, user, timestamp=None):
    output = 'Blub'
    output += ' blub' * random.randint(0, 4)
    rand = random.random()
    if rand > 0.95:
        output += '!'
    elif rand > 0.9:
        output += ','
        output += ' blub' * random.randint(2, 4)
        output += '.' if random.random() > 0.5 else '?'
    elif rand > 0.70:
        output += '?'
    else:
        output += '.'
    SC.api_call(
        "chat.postMessage",
        channel=channel,
        text=output,
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


def initiate_bubbles(context):
    channel = context['channel']

    started_at = time.time()
    # print("OH")
    countdown_duration = context['countdown']
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
                text=BUBBLES_PROMPT(time_left_str, context)
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

    blow_bubbles(context, prompt)

def tabulate_bubbles_for_users(users, default_size, exclusive=None, number_of_groups=None):
    users = set(users)
    groups = []

    if number_of_groups and not default_size:
        default_size = len(users) // number_of_groups

    leftover_users = 0
    try:
        leftover_users = len(users) % default_size if len(users) > default_size else 0
    except Exception as e:
        pass

    logger.info("leftover users %i", leftover_users)
    while len(users) >= default_size:
        group = set()
        size_of_this_group = default_size
        if leftover_users > 0 and not exclusive:
            # add one of our leftover_user to this group
            size_of_this_group += 1
            leftover_users -= 1
        group = random.sample(users, size_of_this_group)
        users.difference_update(group)
        groups.append(group)
    # print(groups)
    return groups

def users_from_emoji_reactions(reactions, bot='UBUBBLES'):
    users = set.union(*[set(e['users']) for e in reactions])
    try:
        users.remove(bot)
    except Exception as e:
        pass
    return users

def blow_bubbles(context, prompt):
    size = context.get('size')
    exclusive = context.get('exclusive')
    number_of_groups = context.get('quantity')

    emoji_reactions = SC.api_call(
        'reactions.get',
        channel=context['channel'],
        timestamp=prompt['ts'],
        full=True
    )['message']['reactions']

    bot_user = context['bot']
    users = users_from_emoji_reactions(emoji_reactions, bot_user)

    logger.info("blowing bubbles for prompt %s", str(context))
    logger.info("with users %s", str(users))

    groups = tabulate_bubbles_for_users(users, size, exclusive, number_of_groups)
    logger.info("and bubbles %s", str(groups))

    group_number = 0
    while len(groups) > 0:
        group = groups.pop()
        if group:
            group_number += 1

        if(context['type'] == 'threaded'):
            bubble = SC.api_call(
                "chat.postMessage",
                channel=context['channel'],
                text=f'bubble # {group_number}... (' + ', '.join(
                    [f'<@{uid}>' for uid in group]) + ')'
            )

            SC.api_call(
                "chat.postMessage",
                thread_ts=bubble['ts'],
                channel=context['channel'],
                text=', '.join(
                    [f'<@{uid}>' for uid in group]) + " :speech_balloon:"
            )
        else:
            bubble = SC.api_call(
                "conversations.open",
                users=",".join(group)
            )

            SC.api_call(
                "chat.postMessage",
                channel=bubble['channel']['id'],
                text=', '.join(
                    [f'<@{uid}>' for uid in group]) + " :speech_balloon:"
            )

    finish_pending_bubbles(
        prompt['ts'], prompt['channel'],
        f'{group_number} bubble{" was" if group_number==1 else "s were"} created.'
    )

    return True

# natural language processing brought to you by regex!
QUANTITY_PATTERN = r"(?:(?:(?:blow)|(?:create)|(?:make)|(?:spawn)|(?:prepare)|(?:synthesize)|(?:give\sus)|(?:let\sus\shave))\s(?P<number>\d*))"
SIZE_PATTERN = r"(?:.*?of\s(?P<size>[\d*\s(or)\-]*))"
SECONDS_PATTERN = r"([\d\.\,]+)\s*(?:s(?:ec)*(?:ond)*(?:s)*)"
MINUTES_PATTERN = r"([\d\.\,]+)\s*(?:m(?:in)*(?:utes)*(?:s)*)"
HOURS_PATTERN = r"([\d\.\,]+)\s*(?:h(?:ou)*(?:r)*(?:s)*)"
DM_PATTERN = r"(direct\smessage(?:s)*|dm(?:s)*)"
THREADS_PATTERN = r"(threads|threaded)"
PROMPTS_PATTERN = r"(?:.*\:\n(?P<prompts>.*))"

# basically just extract whatever info you can get.  if the user decides to use odd grammar, that's on them.
def understand_message(json):
    msg = json['event']['text'].lower()
    context = {
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
        context['cancel'] = thread_ts
        return context
    
    user_intention_count = 0
    try:
        context['quantity'] = int(re.match(QUANTITY_PATTERN, msg)[1])
        user_intention_count += 1
    except Exception as e:
        pass

    try:
        context['seconds'] = float(re.search(SECONDS_PATTERN, msg)[1])
        user_intention_count += 1
    except Exception as e:
        print(e)
        context['seconds'] = 0

    try:
        context['minutes'] = float(re.search(MINUTES_PATTERN, msg)[1])
        user_intention_count += 1
    except Exception as e:
        context['minutes'] = 0

    try:
        context['hours'] = float(re.search(HOURS_PATTERN, msg)[1])
        user_intention_count += 1
    except Exception as e:
        context['hours'] = 0

    try:
        context['prompts'] = re.match(PROMPTS_PATTERN, msg, re.S)[1].split('\n')
        user_intention_count += 1
    except Exception as e:
        pass

    try:
        context['type'] = 'dm' if re.search(DM_PATTERN, msg, re.S)[1] else None
        user_intention_count += 1
    except Exception as e:
        print('error', e)
        context['type'] = None

    try:
        context['type'] = 'threaded' if re.search(THREADS_PATTERN, msg, re.S)[1] else 'dm'
        user_intention_count += 1
    except Exception as e:
        context['type'] = 'threaded' if not 'type' in context else context['type']

    try:
        context['size'] = int(re.match(SIZE_PATTERN, msg)[1])
        user_intention_count += 1
    except Exception as e:
        context['size'] = None if context.get(
            'quantity') or context.get('prompts') else 2

    context['countdown'] = datetime.timedelta(
        minutes=context['minutes'], seconds=context['seconds'], hours=context['hours']\
    ).seconds

    if user_intention_count == 0:
        help_words = ['help', 'how', 'what', 'docs', 'man', 'documentation']
        for h in help_words:
            if h in msg.lower():
                context['help'] = True
                break
        if not context.get('help'):
            context['small_talk'] = True

    return context
