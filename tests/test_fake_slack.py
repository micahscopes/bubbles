import json

def fake_user_message(msg):
    msg.replace('@bubbles', '<@UBUBBLES>')
    json_msg = '''
{"token": "S51fhevuk3FiV5fPdRcSGK9C", "team_id": "TAGFSPMN3", "api_app_id": "AAEU59VJM", "event": {"type": "app_mention", "user": "USER1", "text": "%s", "client_msg_id": "59d32967-7fc6-48ee-a667-d0a3159ac630", "edited": {"user": "UAFJPGW05", "ts": "1530809011.000000"}, "ts": "1530808993.000341", "channel": "CAF7N3MRA", "event_ts": "1530808993.000341"}, "type": "event_callback", "event_id": "EvBKE5Q3R9", "event_time": 1530808993, "authed_users": ["UBKH67PT4"]}
''' % msg
    return json.loads(json_msg)

def fake_user_thread_reply(msg):
    msg.replace('@bubbles', '<@UBUBBLES>')
    json_msg = '''
{"token": "S51fhevuk3FiV5fPdRcSGK9C", "team_id": "TAGFSPMN3", "api_app_id": "AAEU59VJM", "event": {"type": "message", "user": "USER1", "text": "%s", "client_msg_id": "b74877a0-54a0-43d9-b251-c711379b6d78", "thread_ts": "1530809949.000474", "ts": "1530810111.000462", "channel": "CAF7N3MRA", "event_ts": "1530810111.000462", "channel_type": "channel"}, "type": "event_callback", "event_id": "EvBKEJ977D", "event_time": 1530810111, "authed_users": ["UBKH67PT4"]}
''' % msg
    return json.loads(json_msg)

def fake_emoji_reaction(name='bust_in_silhouette', users=['UBUBBLES','USER1']):
    return {'name': name, 'users': users, 'count': len(users)}


def test_message():
    msg = fake_user_message('hey @bubbles')
    # print(msg)
    assert msg['event']['type'] == 'app_mention'

def test_user_thread_reply():
    msg = fake_user_thread_reply('cancel it, @bubbles')
    # print(msg['event'])
    assert 'thread_ts' in msg['event']

def test_emoji_reaction():
    reaction = fake_emoji_reaction('heart_eyes')
    # print(reaction)
    assert reaction['name'] == 'heart_eyes'