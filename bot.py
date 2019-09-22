import os
import time
import re
import random
from slackclient import SlackClient
import urllib, json
import itertools
import string

# instantiate Slack client with token loaded from enviormental variables
# export SLACK_BOT_TOKEN = 'slackbottoken';
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
# starterbot's user ID in Slack: value is assigned after the bot starts up
bot_id = None

# constants
RTM_READ_DELAY = .1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+)>(.*)"

# Load emoji names
url = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"
urlOpen = urllib.urlopen(url)
emojiJson = json.loads(urlOpen.read())

# replace "_" with " " since that is what people will type
EMOJIS = []
for emoji in emojiJson:
    name = emoji['short_name']
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
def add_reactions(responses, channel, timestamp):
    for response in responses:
        response = response.replace(' ','_')
        print 'Reacted with: ' + response
        slack_client.api_call("reactions.add", channel=channel, timestamp = timestamp, name = response)

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Reaction Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        bot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            responses, channel, timestamp = parse_message(slack_client.rtm_read())
            if responses:
                add_reactions(responses, channel, timestamp)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
