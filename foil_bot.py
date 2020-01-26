import os
import subprocess
import shlex
import time
import re
import random
import urllib.request
import urllib.parse
import json
import itertools
import string

from slack import RTMClient

# constants and globals
RTM_READ_DELAY = .1 # 1 second delay between reading from RTM
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CURL_TOKEN = os.environ["SLACK_CURL_TOKEN"]
USER_ID = os.environ["SLACK_BOT_ID"]


def sortByKey(val):
    return val["title"]

# Get the foil price in USD
def getFoilPrice(cardName):
    cardUrl = "https://api.scryfall.com/cards/search?order=set&q=!"+ urllib.parse.quote('"' + cardName + '"') + "&unique=prints"
    with urllib.request.urlopen(cardUrl) as url:
        data = url.read()
        encoding = url.info().get_content_charset('utf-8')

    cardData = json.loads(data.decode(encoding))

    fields = []
    if "data" in cardData:
        for card in cardData["data"]:
            if "prices" in card:
                prices = card["prices"]
                if "usd_foil" in prices and "set_name" in card:
                    if prices["usd_foil"] != None:
                        newField = {}
                        newField["title"] = card["set_name"]
                        newField["value"] = "$" + str(prices["usd_foil"])
                        newField["short"] = True
                        fields.append(newField)
        fields.sort(key=sortByKey)
        return fields 

def postMessage(channel, webClient, attachments):
        webClient.chat_postMessage(channel=channel, text="", attachments=attachments)

@RTMClient.run_on(event="message")
def react_to_post(**payload):
    data = payload['data']
    webClient = payload['web_client']
    channel = data['channel']

    if('bot_id' not in data):
        return
    if(data['bot_id'] == USER_ID):
        return
    if('attachments' not in data):
        return
    if(len(data['attachments']) == 0):
        return

    for attachment in range(0, len(data['attachments'])):
        if('title' not in data["attachments"][attachment]):
            return
        titleSplit = data["attachments"][attachment]["title"].split("Prices for ")
        if len(titleSplit) < 2:
            return

        cardName = titleSplit[1]
        attachments = data["attachments"]
        fields = getFoilPrice(cardName)
        attachments[attachment]["fields"] = fields
        attachments[attachment]["title"] = "Foil prices for " + cardName

    if len(fields) == 0:
        return
    postMessage(channel, webClient, attachments)


if __name__ == "__main__":
    slack_client = RTMClient(
        token=SLACK_TOKEN,
        connect_method='rtm.start'
    )
    print("starting client")
    slack_client.start()
