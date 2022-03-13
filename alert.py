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
        

def alert_discord(message, retry_count=3):
    return _alert_discord(DISCORD_WEBHOOK, message, retry_count=retry_count)

def job_injective_auction_comming():
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

    coming_auction = current_round(auctions.auctions)
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

def init():
    load_dotenv()
    global DISCORD_WEBHOOK
    DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

def main():
    init()
    try:
        while True:
            job_injective_auction_comming()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        appLog.info("done")
        return

if __name__ == "__main__":
    main()
