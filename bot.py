import os
import subprocess
import shlex
import time
import re
import random
import urllib.request
import json
import itertools
import string

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract


from slack import RTMClient

# constants and globals
RTM_READ_DELAY = .1 # 1 second delay between reading from RTM
EMOJIS = []
EMOJIS_UNDERSCORE = []
EMOJIS_DASH = []
WORKSPACE_EMOJIS_DASH = []
WORKSPACE_EMOJIS_UNDERSCORE = []
POKEMON = []
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CURL_TOKEN = os.environ["SLACK_CURL_TOKEN"]
USER_ID = os.environ["SLACK_BOT_ID"]
MIN_EMOJI_LENGTH = 2

# the will get loaded in from json files
CUSTOM_EMOJIS = {}
CUSTOM_USER_EMOJIS = {}
BLACKLIST = []
USERS = {}

OCR = True

def checkIfReactionExists(reaction):
    global EMOJIS
    global EMOJIS_UNDERSCORE
    global EMOJIS_DASH
    global WORKSPACE_EMOJIS_DASH
    global WORKSPACE_EMOJIS_UNDERSCORE
    if reaction in EMOJIS:
        print('emojis')
        return True
    if reaction.replace("_", " ") in EMOJIS_UNDERSCORE:
        print('emojis under')
        return True
    if reaction.replace("_", " ") in EMOJIS_DASH:
        print('emojis dash')
        return True
    if reaction.replace("_", " ") in WORKSPACE_EMOJIS_UNDERSCORE:
        print('workspace underscore')
        return True
    elif reaction.replace("-", " ") in WORKSPACE_EMOJIS_DASH:
        print('workspace dash')
        return True
    else:
        print("False")
        return False

def listCommands(words, channel, userName, webClient):
    webClient.chat_postMessage(channel=channel, text="my commands are:\n"+"\n".join(COMMANDS.keys()))

def addReaction(words, channel, userName, webClient):
    global CUSTOM_EMOJIS
    global CUSTOM_USER_EMOJIS
    if len(words) < 2 or len(words) > 3:
        webClient.chat_postMessage(channel=channel, text="Command Error! Command formats are:\nadd phrase emoji-name\nadd \"multi word phrase\" emoji-name\nadd @username phrase emoji-name")
        return

    if len(words) == 2:
        phrase = words[0]
        if('::skin-tone' in words[1]):
            reaction = words[1].lower()[1:-1]
        else:
            reaction = words[1].lower().replace(":","")
            print(checkIfReactionExists(reaction))
        text = ""

        if len(phrase) < 3:
            webClient.chat_postMessage(channel=channel, text="Command Error! Phrase must be at least 3 characters. Command formats are:\nadd phrase emoji-name\nadd \"multi word phrase\" emoji-name\nadd @username phrase emoji-name")
            return
        print(reaction)

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
            print(userName + " ------ " + text)
            webClient.chat_postMessage(channel=channel, text= text)


    elif len(words) == 3:
        user = words[0]
        phrase = words[1]
        if('::skin-tone' in words[2]):
            reaction = words[2].lower()[1:-1]
        else:
            reaction = words[2].lower().replace(":","")

        text = ""

        if user not in USERS:
            webClient.chat_postMessage(channel=channel, text="Command Error! That user doesn't exist. Command formats are:\nadd phrase emoji-name\nadd \"multi word phrase\" emoji-name\nadd @username phrase emoji-name")
            return

        if len(phrase) < 3:
            webClient.chat_postMessage(channel=channel, text="Command Error! Phrase must be at least 3 characters. Command formats are:\nadd phrase emoji-name\nadd \"multi word phrase\" emoji-name\nadd @username phrase emoji-name")
            return

        if user not in CUSTOM_USER_EMOJIS:
            CUSTOM_USER_EMOJIS[user] = {}

        if phrase in CUSTOM_USER_EMOJIS[user]:
            text = "Replaced"

        CUSTOM_USER_EMOJIS[user][phrase] = reaction
        with open("custom_user_emojis.json", "w") as json_file:
            newEmojis = json.dumps(CUSTOM_USER_EMOJIS, indent=4)
            json_file.write(newEmojis)
            if text == "":
                text += "Added"
            text += " reaction! Now whenever " + user + " says \"" + phrase + "\" I will react with :" + reaction + ":"
            print(userName + " ------ " + text)
            webClient.chat_postMessage(channel=channel, text= text)



def removeReaction(words, channel, userName, webClient):
    if len(words) < 1 or len(words) > 2:
        webClient.chat_postMessage(channel=channel, text="Command Error! Command formats are:\nremove phrase\nremove @username phrase")
        return

    if len(words) == 1:
        phrase = words[0]
        if phrase not in CUSTOM_EMOJIS:
            webClient.chat_postMessage(channel=channel, text="Command Error! That phrase does not exist! Command formats are:\nremove phrase\nremove @username phrase")
            return

        with open("custom_emojis.json", "w") as json_file:
            webClient.chat_postMessage(channel=channel, text="Removed reaction! Now I will not react to \"" + phrase + "\" with :" + CUSTOM_EMOJIS[phrase] + ":")
            del CUSTOM_EMOJIS[phrase]
            newEmojis = json.dumps(CUSTOM_EMOJIS, indent=4)
            json_file.write(newEmojis)
    elif len(words) == 2:
        user = words[0]
        phrase = words[1]
        if user not in CUSTOM_USER_EMOJIS:
            CUSTOM_USER_EMOJIS[user] = {}
        if phrase not in CUSTOM_USER_EMOJIS[user]:
            webClient.chat_postMessage(channel=channel, text="Command Error! This phrase doesn't exist for that user! Command formats are:\nremove phrase\nremove @username phrase")
            return

        with open("custom_user_emojis.json", "w") as json_file:
            webClient.chat_postMessage(channel=channel, text="Removed reaction! Now I will not react with :" + CUSTOM_USER_EMOJIS[user][phrase] + ": when "+ user + " says \"" + phrase + '"')
            del CUSTOM_USER_EMOJIS[user][phrase]
            newEmojis = json.dumps(CUSTOM_USER_EMOJIS, indent=4)
            json_file.write(newEmojis)


def listReactions(words, channel, userName, webClient):
    global CUSTOM_EMOJIS
    global CUSTOM_USER_EMOJIS
    global USERS
    formatted = CUSTOM_EMOJIS.copy()

    for phrase in list(formatted.keys()):
        if "skin-tone" in formatted[phrase]:
            formatted[phrase] = formatted[phrase]
        else:
            formatted[phrase] = ":"+formatted[phrase]+":"
        if phrase in USERS:
            formatted[USERS[phrase]] = formatted[phrase]
            del formatted[phrase]
    reactionList = json.dumps(formatted, sort_keys=True, indent = 4)

    formatted = CUSTOM_USER_EMOJIS.copy()
    for user in formatted.keys():
        for phrase in list(formatted[user].keys()):
            if "skin-tone" in formatted[user][phrase]:
                formatted[user][phrase] = formatted[user][phrase]
            else:
                formatted[user][phrase] = ":" + formatted[user][phrase].replace(":","") + ":"
            if phrase in USERS:
                formatted[user][USERS[phrase]] = user[phrase]
                del formatted[user][phrase]
        if user in USERS:
            formatted[USERS[user]] = formatted[user]
            del formatted[user]
    userReactionList = json.dumps(formatted, sort_keys=True, indent = 4)


    text="These are the current phrase:emoji relations:\n" + reactionList
    text+="\n\n\n These are the current user:phrase:emoji relations:\n" + userReactionList
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
    channel = data['channel']
    ts = data['ts']
    imageText = ""

    if(('bot_id' in data)):
        return

    postedImagesText = ""
    if(('files' in data) == True):
        if(len(data['files']) > 0 and OCR ):
            for postedFile in data['files']:
                url = postedFile['url_private']
                mimetype = postedFile['mimetype']
                name = "./images/" + postedFile['name']
                if('image' in mimetype):
                    subprocess.run(["curl", "-X", "GET", "-H", SLACK_CURL_TOKEN, url, "-o", name])
                    postedImageText = pytesseract.image_to_string(Image.open(name))
                    print("name: " + name + "\ntext: " + postedImageText)
                    postedImagesText += '\n' + postedImageText + '\n'


    if(('text' in data) == False):
        if(postedImagesText != ""):
            responses = create_responses(postedImagesText, currentUserId)
            add_reactions(responses, channel, ts, webClient)
            return
        else:
            return
    else:
        data['text'] += '\n' + postedImagesText

    users = webClient.users_list()
    for user in users['members']:
        userId = "<@" + user['id'] + ">"
        USERS[userId] = user['name']

        if data['user'] == user['id']:
            currentUserName = user['name']
            currentUserId = "<@" + user['id'] + ">"


    wasMentioned = parse_mention(data['text'], channel, currentUserName, webClient)

    if wasMentioned == False:
        responses = create_responses(data['text'], currentUserId)
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
    global EMOJIS_UNDERSCORE
    global EMOJIS_DASH
    global CUSTOM_EMOJIS
    global CUSTOM_USER_EMOJIS
    global POKEMON

    # map custom words to emojis that might be custom in the slack workspace
    with open("custom_emojis.json") as json_file:
        CUSTOM_EMOJIS = json.load(json_file)

    # map custom words to emojis that might be custom in the slack workspace for specific users
    with open("custom_user_emojis.json") as json_file:
        CUSTOM_USER_EMOJIS = json.load(json_file)

    # Load emoji names
    gitUrl = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"
    with urllib.request.urlopen(gitUrl) as url:
        data = url.read()
        encoding = url.info().get_content_charset('utf-8')

    emojiJson = json.loads(data.decode(encoding))

    # replace "_" with " " since that is what people will type
    for emoji in emojiJson:
        for name in emoji['short_names']:
            if '_' in name and '-' in name:
                print("throwing away " + name)
            elif '_' in name:
                name = name.replace('_',' ')
                if len(name) >= MIN_EMOJI_LENGTH:
                    EMOJIS_UNDERSCORE.append(name)
            elif '-' in name:
                name = name.replace('-',' ')
                if len(name) >= MIN_EMOJI_LENGTH:
                    EMOJIS_DASH.append(name)
            else:
                EMOJIS.append(name)

    # Load custom workspace emoji names
    workspaceEmojisRaw = list(json.loads(subprocess.check_output(["curl", "-X", "POST", "-H", SLACK_CURL_TOKEN, "https://slack.com/api/emoji.list"]))['emoji'].keys())
    for emoji in workspaceEmojisRaw:
        if '-' in emoji and '_' in emoji:
            print(emoji + " thrown away!!")
        elif '-' in emoji:
            emoji = emoji.replace('-',' ')
            WORKSPACE_EMOJIS_DASH.append(emoji)
        elif '_' in emoji:
            if emoji.index('_') == 0:
                emoji = emoji.replace('_','')
                POKEMON.append(emoji)
            else:
                emoji = emoji.replace('_',' ')
                WORKSPACE_EMOJIS_UNDERSCORE.append(emoji)
        else:
            WORKSPACE_EMOJIS_UNDERSCORE.append(emoji)


# returns all sequences of n size ((s1,s2,..,sn),(s2,s3,..,sn)),...
def nWise(iterable, n=2):
    iterableList = itertools.tee(iterable, n)
    for i in range(len(iterableList)):
        for j in range(i):
            next(iterableList[i], None)
    return zip(*iterableList)

# looks for phrases and words in a message that are also emoji words
def create_responses(message, userId):
    global EMOJIS
    global EMOJIS_UNDERSCORE
    global EMOJIS_DASH
    global WORKSPACE_EMOJIS_DASH
    global WORKSPACE_EMOJIS_UNDERSCORE
    global CUSTOM_EMOJIS
    global CUSTOM_USER_EMOJIS
    global POKEMON
    responses = []
    # first check for words that are not formatted yet
    unformatted = message.split()
    for word in unformatted:
        if word in CUSTOM_EMOJIS:
            responses.append(CUSTOM_EMOJIS[word])

        if userId in CUSTOM_USER_EMOJIS:
            if word in CUSTOM_USER_EMOJIS[userId]:
                responses.append(CUSTOM_USER_EMOJIS[userId][word])

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
                if wordGroup in POKEMON:
                    wordGroup = '_' + wordGroup
                    responses.append(wordGroup)
                if wordGroup in EMOJIS_UNDERSCORE:
                    wordGroup = wordGroup.replace(' ','_')
                    responses.append(wordGroup)
                if wordGroup in EMOJIS_DASH:
                    wordGroup = wordGroup.replace(' ','-')
                    responses.append(wordGroup)
                if wordGroup in WORKSPACE_EMOJIS_DASH:
                    wordGroup = wordGroup.replace(' ','-')
                    responses.append(wordGroup)
                if wordGroup in WORKSPACE_EMOJIS_UNDERSCORE:
                    wordGroup = wordGroup.replace(' ','_')
                    responses.append(wordGroup)
                if wordGroup in CUSTOM_EMOJIS.keys():
                    responses.append(CUSTOM_EMOJIS[wordGroup])
                if userId in CUSTOM_USER_EMOJIS:
                    if wordGroup in CUSTOM_USER_EMOJIS[userId]:
                        responses.append(CUSTOM_USER_EMOJIS[userId][wordGroup])

    # get rid of duplicate responses
    responses = list(set(responses))
    return responses
        
# Sends the response back to the channel
def add_reactions(responses, channel, timestamp, webClient):
    global BLACKLIST

    for response in responses:
        if response in BLACKLIST:
            continue

        print ('Reacted with: ' + response)

        webClient.reactions_add(
            channel=channel,
            name=response,
            timestamp=timestamp
        )
        time.sleep(.1)

if __name__ == "__main__":
    load_blacklist()
    load_emojis()
    print("loaded emojis")
    slack_client = RTMClient(
        token=SLACK_TOKEN,
        connect_method='rtm.start'
    )
    print("starting client")
    slack_client.start()
