from flask import Flask, request
from threading import Thread
from slackclient import SlackClient
from src.bubbles import initiate_bubbles, parse_message, finish_pending_bubbles, give_help
app = Flask(__name__)

@app.route('/',methods=['POST','GET'])
def main():
    if not request.is_json:
        return
    json = request.get_json()
    if 'challenge' in json:
        print('received challenge...')
        return str(json['challenge'])
        
    bot = json['authed_users'][0]

    e = json['event']
    if e['type'] == 'app_mention' and 'user' in e and e['user'] != bot:
        print(json)
        info = parse_message(json)

        if 'cancel' in info:
            finish_pending_bubbles(info['cancel'], info['channel'])
        elif 'help' in info:
            give_help(info['channel'], info['user'])
        else:
            # print("INITIATING BUBBLES!!!", info)
            th = Thread(target=initiate_bubbles, args=(info,))
            th.start()
    return ''
