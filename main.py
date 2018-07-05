from flask import Flask, request
from threading import Thread
from slackclient import SlackClient
from bubbles import initiate_bubbles, understand_message, finish_pending_bubbles, give_help
import logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/readiness_check', methods=['GET'])
def readiness_check():
    return 'yes'

@app.route('/health_check', methods=['GET'])
def health_check():
    return 'yes'

@app.route('/',methods=['POST','GET'])
def main():
    if not request.is_json:
        print("request isn't json")
        return 'BUBBLES needs JSON.'
    json = request.get_json()
    # print("REQUEST JSON", json)
    if 'challenge' in json:
        print('received challenge...')
        return str(json['challenge'])
        
    bot = json['authed_users'][0]

    e = json['event']
    if e['type'] == 'app_mention' and 'user' in e and e['user'] != bot:
        # print(json)
        info = understand_message(json)
        print(info)
        if 'cancel' in info:
            finish_pending_bubbles(info['cancel'], info['channel'])
        elif 'help' in info:
            give_help(info['channel'], info['user'])
        elif 'small_talk' in info:
            small_talk(info['channel'], info['user'])
        else:
            # print("INITIATING BUBBLES!!!", info)
            th = Thread(target=initiate_bubbles, args=(info,))
            th.start()
    return 'BUBBLES.'

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)
