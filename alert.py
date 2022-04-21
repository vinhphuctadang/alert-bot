"""
author: Phuc Ta (vinhphuctadang@gmail.com)
"""

import logging
from logging import log
from nis import cat
from syslog import LOG_DEBUG, LOG_ERR, LOG_INFO
from pyinjective.constant import Network
from pyinjective.client import Client
import time
from dotenv import load_dotenv
import os
import requests
import json

# wake up and check
INTERVAL = 60 # seconds
DISCORD_WEBHOOK = None
SLACK_WEBHOOK = None

COMMING_AUCTION_ALERT_TEMPLATE="""
Injective Auction Alert
Auction is going to end in next %d minutes.
Link: https://hub.injective.network/auction
"""

# global vars
already_alerted = {}

logging.basicConfig(level=logging.INFO)
appLog = logging.getLogger("alert-bot")

def _alert_discord(webhook, message, retry_count=3):
    appLog.info("going to alert Discord")
    for _ in range(retry_count):
        request_result = requests.post(webhook, data={
            "content": message,
        })

        is_success = True
        if request_result.status_code >= 300:
            is_success = False

        txt = request_result.text
        obj_log = {
            "alerted": message,
            "response": txt,
        }
        appLog.info("%s" % json.dumps(obj_log))
        if is_success:
            return True
    appLog.error("alert to discord failed")
    return False

def _alert_slack(webhook, message, retry_count=3):
    lastErr = ""
    appLog.info("going to alert Slack")
    for _ in range(retry_count):
        request_result = requests.post(webhook, json={
            "text": message,
        })

        is_success = True
        if request_result.status_code >= 300:
            is_success = False

        txt = request_result.text
        obj_log = {
            "alerted": message,
            "response": txt,
        }
        lastErr = txt
        appLog.info("%s" % json.dumps(obj_log))
        if is_success:
            return True
    appLog.error("alert to Slack failed, err: %s" % lastErr)
    return False 

def alert_discord(message, retry_count=3):
    return _alert_discord(DISCORD_WEBHOOK, message, retry_count=retry_count)

def alert_slack(message, retry_count=3):
    return _alert_slack(SLACK_WEBHOOK, message, retry_count=retry_count)


def job_injective_auction_comming():
    appLog.info("job_injective_auction_comming to check for upcoming auction is running")
    ALERT_BEFORE = 15 * 60 # 15 minutes
    def current_round(auctions):
        round, auction = -1, None
        for a in auctions:
            if a.round > round:
                round, auction = a.round, a
        return auction

    network = Network.mainnet(node="sentry0")
    client = Client(network=network, insecure=True)
    try:
        auctions = client.get_auctions()
    except Exception as e:
        appLog.error("get auction failed: " + str(e))
        alert_discord("get_auction ERROR: ```get auction failed: %s```" % str(e))
        return

    coming_auction = current_round(auctions.auctions)
    if coming_auction == None:
        alert_discord("get_auction ERROR: ```coming auction is null```")
        return

    end_time = coming_auction.end_timestamp / 1000

    if already_alerted.get(coming_auction.round, False):
        return

    now = time.time()
    if now < end_time and end_time - now < ALERT_BEFORE:
        minutes = int((end_time - now) / 60)
        alert_result = alert_discord(COMMING_AUCTION_ALERT_TEMPLATE % minutes)
        if alert_result:
            already_alerted[coming_auction.round] = True
    else:
        appLog.debug("cannot alert:", end_time - now, end_time - now < ALERT_BEFORE)

def job_injective_bayc_price():
    MAX_BID_THRE = 90*10**18
    MIN_ASK_THRE = 150*10**18
    BAYC_MARKETID = "0x2d1fc1ebff7cae29d6f85d3a2bb7f3f6f2bab12a25d6cc2834bcb06d7b08fd74"
    network = Network.mainnet(node="sentry0")
    client = Client(network=network, insecure=True)
    orderbook = None

    appLog.info("job_injective_bayc_price to check for BAYC/WETH orderbook")
    try:
        orderbook = client.get_derivative_orderbook(market_id=BAYC_MARKETID)
    except Exception as e:
        alert_slack("get_derivative_orderbook ERROR: ```get orderbook failed: %s```" % str(e))
        return

    maxBidPrice = None
    minAskPrice = None
    for o in orderbook.orderbook.buys:
        price = int(o.price)
        if maxBidPrice == None or maxBidPrice < price: 
            maxBidPrice = price
    for o in orderbook.orderbook.sells:
        price = int(o.price)
        if minAskPrice == None or minAskPrice > price: 
            minAskPrice = price
    # check and alert
    if maxBidPrice < MAX_BID_THRE:
        alert_slack("Hey, BAYC/WETH PERP orderbook has maxBidPrice below %.1fWETH, i.e %d, check please" % (MAX_BID_THRE/(10**18), maxBidPrice))
    
    if minAskPrice >= MIN_ASK_THRE:
        alert_slack("Hey, BAYC/WETH PERP orderbook has minAskPrice above/equal %.1fWETH, i.e %d, check please" % (MIN_ASK_THRE/(10**18), minAskPrice))

def init():
    load_dotenv()
    global DISCORD_WEBHOOK, SLACK_WEBHOOK
    DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
    SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")

def main():
    init()
    try:
        while True:
            job_injective_auction_comming()
            job_injective_bayc_price()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        appLog.info("done")
        return

if __name__ == "__main__":
    main()
