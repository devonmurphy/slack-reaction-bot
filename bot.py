import os
import time
import re
import random
import urllib.request
import json
import itertools
import string

from fuzzywuzzy import process
from slack import RTMClient

# constants and globals
RTM_READ_DELAY = .1 # 1 second delay between reading from RTM
EMOJIS = []
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
USER_ID = os.environ["SLACK_BOT_ID"]
MIN_EMOJI_LENGTH = 3
FUZZY_MATCH = True

MIN_FUZZY_CUSTOM_MATCH_RATIO = 80
MIN_FUZZY_MATCH_RATIO = 85

# map custom words to emojis that might be custom in the slack workspace
CUSTOM_EMOJIS = {
    "monkey":"gix-monkey",
    "gix":"gix-monkey",
    "@gix":"gix-monkey",
    "gaak":"hogaak",
    "gaaked":"hogaak",
    "gaakd":"hogaak",
    "hoogaak":"hogaak",
    "laser":"hogaak",
    "stonks":"stonk-up",
    "good":"stonk-up",
    "stonkz":"stonk-up",
    "bad":"stonk-down",
    "ok":"stonk-flat",
    "party":"party",
    "think":"big-think",
    "big":"big-think",
    "thought":"big-think",
    "money":"money-with-wings",
    "goose":"goose",
}


@RTMClient.run_on(event="message")
def react_to_post(**payload):
    data = payload['data']
    webClient = payload['web_client']
    print('message received')
    if(('text' in data) == False):
        return

    responses = create_responses(data['text'])
    channel = data['channel']
    ts = data['ts']
    add_reactions(responses, channel, ts, webClient)
    parse_mention(data['text'], channel, webClient)
    time.sleep(RTM_READ_DELAY)

def parse_mention(text, channel, webClient):
    if '@'+USER_ID in text:
        print('mentioned')
        webClient.chat_postMessage(
            channel=channel,
            text="I don't have any commands yet,")

def load_emojis():
    global EMOJIS

    # Load emoji names
    gitUrl = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"
    with urllib.request.urlopen(gitUrl) as url:
        data = url.read()
        encoding = url.info().get_content_charset('utf-8')

    emojiJson = json.loads(data.decode(encoding))

    # replace "_" with " " since that is what people will type
    for emoji in emojiJson:
        for name in emoji['short_names']:
            name = name.replace('_',' ')
            if len(name) >= MIN_EMOJI_LENGTH:
                EMOJIS.append(name)


# returns all sequences of n size ((s1,s2,..,sn),(s2,s3,..,sn)),...
def nWise(iterable, n=2):
    iterableList = itertools.tee(iterable, n)
    for i in range(len(iterableList)):
        for j in range(i):
            next(iterableList[i], None)
    return zip(*iterableList)

def parse_message(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
                responses = create_responses(event["text"])
                return responses, event["channel"], event["ts"]
    return None, None, None

# looks for phrases and words in a message that are also emoji words
def create_responses(message):
    for c in string.punctuation:
        message = message.replace(c,"")
    words = message.lower().split()
    responses = []
    subsets = []
    for wordCount in range(1,5):
        subsets.append(nWise(words, wordCount))
    
    for subset in subsets:
        if subset != None:
            for wordGroup in subset:
                wordGroup = ' '.join(wordGroup)
                if wordGroup in EMOJIS:
                    responses.append(wordGroup)
                if wordGroup in CUSTOM_EMOJIS.keys():
                    responses.append(CUSTOM_EMOJIS[wordGroup])


    if FUZZY_MATCH and len(responses) == 0:
        for word in words:
            result = process.extractOne(word, CUSTOM_EMOJIS.keys())
            if result[1] > MIN_FUZZY_CUSTOM_MATCH_RATIO:
                print("FUZZY CUSTOM MATCH: " + result[0])
                print("FUZZY CUSTOM RATIO: " + str(result[1]))
                response = CUSTOM_EMOJIS[result[0]]
                responses.append(response)
            else:
                result = process.extractOne(word, EMOJIS)
                if result[1] > MIN_FUZZY_MATCH_RATIO:
                    print("FUZZY MATCH: " + result[0])
                    print("FUZZY RATIO: " + str(result[1]))
                    response = result[0]
                    responses.append(response)

    return responses
        
# Sends the response back to the channel
def add_reactions(responses, channel, timestamp, webClient):
    for response in responses:
        response = response.replace(' ','_')
        print ('Reacted with: ' + response)

        webClient.reactions_add(
            channel=channel,
            name=response,
            timestamp=timestamp
        )

if __name__ == "__main__":
    load_emojis()
    slack_client = RTMClient(
        token=SLACK_TOKEN,
        connect_method='rtm.start'
    )
    slack_client.start()
