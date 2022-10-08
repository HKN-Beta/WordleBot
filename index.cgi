#! /usr/bin/env python3

import os
import sys
import cgi
import re
import json
import requests

with open("../../private/wordlebot/wordlebot_token", "r") as f:
    BOT_TOKEN = f.read().strip()
URL_ENCODED = {"Content-Type": "application/x-www-form-urlencoded"}

def validate_wordle(msg):
    try:
        lines = msg.split("\n")
        match = re.match(r'^Wordle [0-9]+ ([0-9]+|X)/[0-9]+\*?$', lines[0])
        assert match
        if "X/6" in lines[0]:
            expected = 6
        else:
            expected = int(match[1])
        # find next line that has the word "square"
        start = -1
        for i,line in enumerate(lines):
            start = lines.index(line)
            if "square" in line:
                break
        assert start > 0 and start < len(lines) and (start + expected - 1) < len(lines)
        for line in lines[start:start+expected-1]:
            if not all(c in line for c in ["square", "large", ":", "_"]):
                assert False
        return True
    except Exception as e:
        with open("errlog", "a+") as f:
            f.write(str(e) + "\n")
        return False

def update_score(scr):
    # check how many times name appears in .wordle/XXX
    wordle_path = os.path.join(".wordles", str(scr["wordle_id"]))
    if not os.path.exists(wordle_path):
        with open(wordle_path, "a+") as f:
            f.write(str(scr["name"]) + "\n")
    else:
        with open(wordle_path, "r") as f:
            names = f.read()
        if scr["name"] in names:
            # HEY! You already got a point for this wordle!
            return
        else:
            with open(wordle_path, "a+") as f:
                f.write(str(scr["name"]) + "\n")
    if not os.path.exists("scores.json"):
        scores = {}
    else:
        with open("scores.json", "r") as f:
            scores = json.load(f)
    name = scr["name"]
    scr = scr["score"]
    if name not in scores:
        scores[name] = {"points": scr, "played": 1}
    else:
        scores[name] = {"points": scores[name]["points"] + scr, "played": scores[name]["played"] + 1}
    with open("scores.json", "w+") as f:
        json.dump(scores, f)

def save_json(data):
    idx = 0
    filename = "recv.json.%d" % idx
    while os.path.exists(filename):
        idx += 1
        filename = "recv.json.%d" % idx
    with open(filename, "w+") as f:
        json.dump(data, f)

def save_msg(data):
    idx = 0
    filename = "msg.%d" % idx
    while os.path.exists(filename):
        idx += 1
        filename = "msg.%d" % idx
    with open(filename, "w+") as f:
        f.write(data)

if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        # save_json(payload)
        if "event" in payload:
            if "subtype" in payload["event"] and payload["event"]["subtype"] == "channel_join":
                # we were just added to the channel and should send a hello message
                data = {"token": BOT_TOKEN, "channel": payload["event"]["channel"], 
                        "text": "Hello, fellow Wordlers!  I'd like to help you out by handling your Wordle scores.  I've just scraped the scores from today, and " + 
                                "I'll be keeping track of them from now on.  If you'd like to see the current scores, head over to https://engineering.purdue.edu/hkn/wordlebot/ for the latest scores.  " + 
                                "May the best person win (but that doesn't mean any of you deserve any less 💓)!"}
                requests.post("https://slack.com/api/chat.postMessage", data=data, headers=URL_ENCODED)
                data = {"token": BOT_TOKEN, "channel": payload["event"]["channel"], 
                        "text": "I'm doing my best to understand the messages you send, but sometimes I get confused.  You can help by not modifying the copied text you get from the Wordle page, " +
                                 "and just pasting it directly with no other characters into the box.  If you think I've made a mistake, please let Niraj know!"}
                requests.post("https://slack.com/api/chat.postMessage", data=data, headers=URL_ENCODED)
                print("Content-Type: text/json\r\n")
                print(json.dumps({"status": "ok"}))
            elif "user" in payload["event"]:
                userpayload = {"token": BOT_TOKEN, "user": payload["event"]["user"]}
                r = requests.post("https://slack.com/api/users.info", data=userpayload)
                realname = r.json()["user"]["real_name"]
                message_text = payload["event"]["text"]
                # debug only
                # save_msg(realname + ": " + message_text)
                if validate_wordle(message_text):
                    if "X/6" in message_text:
                        evt = { "name": realname, "score": 0 }
                    else:
                        score = re.findall(r"Wordle ([0-9]+) (([0-9]+)/([0-9]+))", message_text)
                        number = int(score[0][0])
                        solved = int(score[0][2])
                        total = int(score[0][3])
                        assert solved <= total and solved > 0 and total > 0
                        evt = { "name": realname, "wordle_id": number, "score": (total - solved + 1) }
                    update_score(evt)
        print("Content-Type: text/json\r\n")
        print(json.dumps({"status": "ok"}))
    except Exception as e:
        if os.environ["REQUEST_METHOD"] == "POST":
            with open("errlog", "a+") as f:
                f.write(str(e) + "\n")
        print("Content-Type: text/html\r\n")
        with open("scores.html") as f:
            print(f.read())
