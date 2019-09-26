import os
import time
import re
import random
import urllib.request
import json
import itertools
import string

from slack import RTMClient

@RTMClient.run_on(event="message")
def react_to_post(**payload):
    data = payload['data']
    web_client = payload['web_client']
    print('message received')
    if(('text' in data) == False):
        return

    responses = create_responses(data['text'])
    channel_id = data['channel']
    ts = data['ts']
    add_reactions(responses, channel_id, ts, web_client)
    time.sleep(RTM_READ_DELAY)

# constants
RTM_READ_DELAY = .1 # 1 second delay between reading from RTM

# Load emoji names
gitUrl = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"
with urllib.request.urlopen(gitUrl) as url:
    data = url.read()
    encoding = url.info().get_content_charset('utf-8')

emojiJson = json.loads(data.decode(encoding))

# replace "_" with " " since that is what people will type
EMOJIS = []
for emoji in emojiJson:
    for name in emoji['short_names']:
        name = name.replace('_',' ')
        if len(name) > 1:
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
    return responses
        
# Sends the response back to the channel
def add_reactions(responses, channel, timestamp, web_client):
    for response in responses:
        response = response.replace(' ','_')
        print ('Reacted with: ' + response)

        web_client.reactions_add(
            channel=channel,
            name=response,
            timestamp=timestamp
        )

if __name__ == "__main__":
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_client = RTMClient(
        token=slack_token,
        connect_method='rtm.start'
    )
    slack_client.start()
