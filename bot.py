import os
import shlex
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
MIN_EMOJI_LENGTH = 2

FUZZY_MATCH = False
MIN_FUZZY_CUSTOM_MATCH_RATIO = 60

# the will get loaded in from json files
CUSTOM_EMOJIS = {}
BLACKLIST = []
USERS = {}

def listCommands(words, channel, userName, webClient):
    webClient.chat_postMessage(channel=channel, text="my commands are:\n"+"\n".join(COMMANDS.keys()))

def addReaction(words, channel, userName, webClient):
    if len(words) != 2:
        webClient.chat_postMessage(channel=channel, text="Command Error! command format is:\nadd phrase emoji-name")
        return

    phrase = words[0]
    reaction = words[1].lower().replace(":","")
    text = ""

    if len(phrase) < 3:
        webClient.chat_postMessage(channel=channel, text="Command Error! phrase must be atleast 3 characters. Command format is:\nadd phrase emoji-name")
        return


    if phrase in CUSTOM_EMOJIS:
        text = "Replaced"

    CUSTOM_EMOJIS[phrase] = reaction
    #CUSTOM_EMOJIS[phrase] = { "reaction": reaction, "user": userName}

    with open("custom_emojis.json", "w") as json_file:
        newEmojis = json.dumps(CUSTOM_EMOJIS, indent=4)
        json_file.write(newEmojis)
        if text == "":
            text += "Added"
        text += " reaction! Now whenever \"" + phrase + "\" is said I will react with :" + reaction + ":"
        webClient.chat_postMessage(channel=channel, text= text)

def removeReaction(words, channel, userName, webClient):
    if len(words) < 1:
        webClient.chat_postMessage(channel=channel, text="Command Error! command format is:\nremove phrase")
        return

    phrase = words[0]
    if phrase not in CUSTOM_EMOJIS:
        webClient.chat_postMessage(channel=channel, text="Command Error! This phrase doesn't exist!")
        return

    with open("custom_emojis.json", "w") as json_file:
        newEmojis = json.dumps(CUSTOM_EMOJIS, indent=4)
        json_file.write(newEmojis)
        webClient.chat_postMessage(channel=channel, text="Removed reaction! Now I will not react to " + phrase + " with :" + CUSTOM_EMOJIS[phrase] + ":")
        del CUSTOM_EMOJIS[phrase]

def listReactions(words, channel, userName, webClient):
    global CUSTOM_EMOJIS
    global USERS
    formatted = dict(CUSTOM_EMOJIS)

    for phrase in list(formatted.keys()):
        print(phrase)
        formatted[phrase] = ":"+formatted[phrase]+":"
        if phrase in USERS:
            formatted[USERS[phrase]] = formatted[phrase]
            del formatted[phrase]

    reactionList = json.dumps(formatted, sort_keys=True, indent = 4)
    text="These are the current phrase:emoji relations:\n" + reactionList
    webClient.chat_postMessage(channel=channel,text=text)

def blacklist(words, channel, userName, webClient):
    global BLACKLIST
    if len(words) < 1:
        formatted = BLACKLIST.copy()
        index = 0
        for word in formatted:
            formatted[index] = ":"+word+":"
            index += 1
        text="The emojis that are blacklisted currently are:\n" + "\n".join(formatted)+"\n\n\n"
        text+="If you would like to blacklist an emoji, the command format is:\nblacklist emoji-name"
        webClient.chat_postMessage(channel=channel,text=text) 
        return

    with open("blacklist.json", "w") as json_file:
        reaction = words[0]
        if reaction not in BLACKLIST:
            BLACKLIST.append(reaction)
            newBlacklist = json.dumps({ "blacklist": BLACKLIST }, indent=4)
            json_file.write(newBlacklist)
            webClient.chat_postMessage(channel=channel, text="Blacklisted reaction! Now I won't use :" + reaction + ": as a reaction")
        else:
            webClient.chat_postMessage(channel=channel, text=":" + reaction + ": is already blacklisted")

def unblacklist(words, channel, userName, webClient):
    global BLACKLIST
    if len(words) < 1:
        formatted = BLACKLIST.copy()
        index = 0
        for word in formatted:
            formatted[index] = ":"+word+":"
            index += 1
        text="The emojis that are blacklisted currently are:\n" + "\n".join(formatted)+"\n\n\n"
        text+="If you would like to unblacklist an emoji, the command format is:\nunblacklist emoji-name"
        webClient.chat_postMessage(channel=channel,text=text) 
        return

    with open("blacklist.json", "w") as json_file:
        reaction = words[0]
        if reaction in BLACKLIST:
            BLACKLIST.remove(reaction)
            newBlacklist = json.dumps({ "blacklist": BLACKLIST }, indent=4)
            json_file.write(newBlacklist)
            webClient.chat_postMessage(channel=channel, text="Unblacklisted reaction! Now I will use :" + reaction + ": as a reaction")
        else:
            webClient.chat_postMessage(channel=channel, text=":" + reaction + ": is not blacklisted, feel free to use it")

COMMANDS = {
    "help": listCommands,
    "blacklist": blacklist,
    "unblacklist": unblacklist,
    "add": addReaction,
    "remove": removeReaction,
    "list": listReactions
}

@RTMClient.run_on(event="message")
def react_to_post(**payload):
    global USER_ID
    global USERS
    data = payload['data']
    webClient = payload['web_client']

    if(('bot_id' in data)):
        return

    if(('text' in data) == False):
        return

    users = webClient.users_list()
    for user in users['members']:
        if data['user'] == user['id']:
            userName = user['name']

        userId = "<@" + user['id'] + ">"
        USERS[userId] = user['name']

    channel = data['channel']
    ts = data['ts']
    wasMentioned = parse_mention(data['text'], channel, userName, webClient)

    if wasMentioned == False:
        responses = create_responses(data['text'])
        add_reactions(responses, channel, ts, webClient)


def parse_mention(text, channel, userName, webClient):
    global USER_ID
    if '@' + USER_ID in text:
        commandFound = False
        text = text.replace('“','"')
        text = text.replace('”','"')
        try:
            words = shlex.split(text)
        except:
            words = []
        print(words)
        index = 0
        for word in words:
            if word in COMMANDS.keys():
                COMMANDS[word](words[index + 1:], channel, userName, webClient)
                commandFound = True
                break
            index += 1

        if commandFound == False:
            webClient.chat_postMessage(channel=channel, text="I don't have that command yet.")
            listCommands(words, channel, userName, webClient)
        return True
    else:
        return False

def load_blacklist():
    global BLACKLIST

    # open blacklisted words
    with open("blacklist.json") as json_file:
        BLACKLIST = json.load(json_file)['blacklist']


def load_emojis():
    global EMOJIS
    global CUSTOM_EMOJIS

    # map custom words to emojis that might be custom in the slack workspace
    with open("custom_emojis.json") as json_file:
        CUSTOM_EMOJIS = json.load(json_file)

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

# looks for phrases and words in a message that are also emoji words
def create_responses(message):
    global EMOJIS
    global CUSTOM_EMOJIS
    responses = []
    # first check for words that are not formatted yet
    unformatted = message.split()
    for word in unformatted:
        if word in CUSTOM_EMOJIS:
            responses.append(CUSTOM_EMOJIS[word])

    for c in string.punctuation:
        message = message.replace(c,"")

    words = message.lower().split()
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
            if(len(word) < 4):
                break

            result = process.extractOne(word, CUSTOM_EMOJIS.keys())
            if result[1] > MIN_FUZZY_CUSTOM_MATCH_RATIO:
                print("FUZZY CUSTOM MATCH: " + result[0])
                print("FUZZY CUSTOM RATIO: " + str(result[1]))
                response = CUSTOM_EMOJIS[result[0]]
                responses.append(response)

    return responses
        
# Sends the response back to the channel
def add_reactions(responses, channel, timestamp, webClient):
    global BLACKLIST

    for response in responses:
        if response in BLACKLIST:
            break

        response = response.replace(' ','_')
        print ('Reacted with: ' + response)

        webClient.reactions_add(
            channel=channel,
            name=response,
            timestamp=timestamp
        )

if __name__ == "__main__":
    load_blacklist()
    load_emojis()
    slack_client = RTMClient(
        token=SLACK_TOKEN,
        connect_method='rtm.start'
    )
    slack_client.start()
