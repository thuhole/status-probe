from github import Github
from datetime import datetime
import os
import logging
import requests
import json
import hashlib
import time
import base64

REFRESH_INTERVAL = 60
TIMEOUT = 10
TOLERATE_FAIL_TIMES = 2

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s")


def checkConnection(url, code):
    try:
        r = requests.get(
            url, headers={"User-Agent": "cState_Probe/0.0.1"}, timeout=TIMEOUT, allow_redirects=False)
        logging.debug(str(r.elapsed.total_seconds()) +
                      "s elapsed to get " + url)
        if r.status_code == code:
            return True
        else:
            logging.warning("inconsistent status code for " + url +
                            ", expecting " + str(code) + ", got " + str(r.status_code))
            return False
    except Exception as e:
        logging.warning("failed to get " + url + ", err=" + str(e))
        return False


def publishServiceOnline(repo, name):
    try:
        contents = repo.get_contents("content/issues/")
        for content_file in contents:
            c = repo.get_contents(content_file.path)
            decoded_content = base64.b64decode(c.content).decode("utf-8")
            print(decoded_content, "- " + name in decoded_content,
                  "resolved: false" in decoded_content)
            if "- " + name in decoded_content and "resolved: false" in decoded_content:
                date = datetime.utcnow().isoformat("T") + "Z"
                newContent = decoded_content.replace(
                    "resolved: false", "resolved: true")
                newContent = newContent.replace(
                    "resolvedWhen: \"\"", "resolvedWhen: " + date)
                repo.update_file(c.path,
                                 "update " + c.name, newContent, c.sha)
                return
    except Exception as e:
        logging.warning("error while publishServiceOnline, err=" + str(e))


def publishServiceOffline(repo, name):
    filename = datetime.now().strftime("%Y-%m-%d %H:%M:%S.md")
    date = datetime.utcnow().isoformat("T") + "Z"
    content = """---
section: issue
title: Disruption Detected
date: {}
resolved: false
informational: false
resolvedWhen: ""
affected:
  - {}
severity: disrupted
---
*Investigating* - We are investigating a potential issue that might affect the uptime of one our of services. We are sorry for any inconvenience this may cause you. This incident post will be updated once we have more information.

This is an automatic post by a monitor bot.
""".format(date, name)
    try:
        repo.create_file("content/issues/" + filename,
                         "create " + filename, content)
    except Exception as e:
        logging.warning("failed to create file at GitHub, err=" + str(e))


if __name__ == '__main__':
    with open('config.json') as f:
        data = json.load(f)
    TOKEN = data["token"]
    g = Github(TOKEN)
    repo = g.get_repo(data["repo"])
    tasks = data["tasks"]
    for task in tasks:
        task["last_success"] = True

    while True:
        for task in tasks:
            task["now_success"] = checkConnection(task["URL"], task["Code"])

        reference_success = all([x["now_success"]
                                 for x in tasks if x["Category"] == "Reference"])
        for task in tasks:
            if task["Category"] != "Reference":
                relative_success = (
                    not reference_success) or task["now_success"]
                task["relative_success"] = relative_success

                if relative_success and (not task["last_success"]):
                    logging.warning(task["Name"] + " online!")
                    publishServiceOnline(repo, task["Name"])
                elif (not relative_success) and task["last_success"]:
                    logging.warning(task["Name"] + " offline!")
                    publishServiceOffline(repo, task["Name"])
                else:
                    logging.info(task["Name"] + " status no change")

                task["last_success"] = task["relative_success"]
        time.sleep(REFRESH_INTERVAL)
