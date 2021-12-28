import json
import logging
import random
import threading
import time
from datetime import datetime
from enum import Enum

import requests
import socket
from github import Github

REFRESH_INTERVAL = 60
TIMEOUT = 10
TOLERATE_FAIL_TIMES = 2

logging.basicConfig(level=logging.DEBUG, handlers=[])
logger = logging.getLogger('MAIN')
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler('warning.log')
c_handler.setLevel(logging.DEBUG)
f_handler.setLevel(logging.WARNING)
c_format = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
f_format = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
# %(asctime)s %(name)-12s %(levelname)-8s %(message)s
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)
logger.addHandler(c_handler)
logger.addHandler(f_handler)

unresolvedIssues = {}
condition = threading.Condition()
q = []


class TaskType(Enum):
    OFFLINE = 0
    ONLINE = 1


class Task:
    def __init__(self, taskType, name, date):
        self.taskType = taskType
        self.date = date
        self.name = name

    def run(self):
        if self.taskType == TaskType.OFFLINE:
            return self.publishOffline()
        elif self.taskType == TaskType.ONLINE:
            return self.publishOnline()

    def publishOffline(self):
        try:
            content = """---
section: issue
title: Disruption Detected - {}
date: {}
resolved: false
informational: false
resolvedWhen: ""
affected:
  - {}
severity: disrupted
---
*Investigating* - We are investigating a potential issue that might affect the uptime of one of our services. We are sorry for any inconveniences this may cause you. This incident post will be updated once we have more information.

This is an automatic post by a monitor bot.
        """.format(self.name, self.date, self.name)
            filename = self.date + ".md"
            r = repo.create_file("content/issues/" + filename,
                                 "create " + filename, content)
            unresolvedIssues[self.name] = {
                "filename": filename,
                "fileSha": r["content"].sha,
                "content": content
            }
            logger.info("GitHub file created.")
            return None
        except Exception as e:
            logger.warning("failed to create file at GitHub, err=" + str(e))
            return e

    def publishOnline(self):
        try:
            if self.name not in unresolvedIssues:
                raise Exception("No unresolved record in dictionary for " + self.name)
            data = unresolvedIssues[self.name]
            newContent = data["content"].replace("resolved: false", "resolved: true")
            newContent = newContent.replace("resolvedWhen: \"\"", "resolvedWhen: " + self.date)
            repo.update_file("content/issues/" + data["filename"],
                             "update " + data["filename"], newContent, data["fileSha"])
            unresolvedIssues.pop(self.name)
            logger.info("GitHub file updated.")
            return None
        except Exception as e:
            logger.warning("failed to update file at GitHub, err=" + str(e))
            return e


def checkConnection(url, code, scheme):
    if scheme.upper() == "HTTP":
        try:
            r = requests.get(url, headers={"User-Agent": "cState_Probe/0.0.1"}, timeout=TIMEOUT, allow_redirects=False)
            logger.debug(str(r.elapsed.total_seconds()) + "s elapsed to get " + url)
            if r.status_code == code:
                return True
            else:
                logger.warning("inconsistent status code for " + url +
                            ", expecting " + str(code) + ", got " + str(r.status_code))
                return False
        except Exception as e:
            logger.warning('failed to get ' + url + ', err=' + str(e))
            return False
    elif scheme.upper() == "TCP":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((url, int(code)))
            s.shutdown(2)
            return True
        except Exception as e:
            logger.warning(f'failed to connect to socket {url}:{code} err={e}')
            return False


class ProducerThread(threading.Thread):
    def __init__(self):
        super(ProducerThread, self).__init__()

    def run(self):
        while True:
            for task in tasks:
                task["now_success"] = checkConnection(task["URL"], task["Code"], task["Scheme"])

            reference_success = all([x["now_success"] for x in tasks if x["Category"] == "Reference"])
            for task in tasks:
                if task["Category"] != "Reference":
                    relative_success = (not reference_success) or task["now_success"]
                    task["relative_success"] = relative_success

                    if relative_success and (not task["last_success"]):
                        logger.warning(task["Name"] + " online!")

                        condition.acquire()
                        q.append(Task(TaskType.ONLINE, task["Name"], datetime.utcnow().isoformat("T") + "Z"))
                        condition.notify()
                        condition.release()
                    elif (not relative_success) and task["last_success"]:
                        logger.warning(task["Name"] + " offline!")

                        condition.acquire()
                        q.append(Task(TaskType.OFFLINE, task["Name"], datetime.utcnow().isoformat("T") + "Z"))
                        condition.notify()
                        condition.release()
                    else:
                        logger.info(task["Name"] + " status no change")

                    task["last_success"] = task["relative_success"]
            time.sleep(REFRESH_INTERVAL)


class ConsumerThread(threading.Thread):
    def __init__(self):
        super(ConsumerThread, self).__init__()

    def run(self):
        while True:
            condition.acquire()
            if not q:
                logger.debug("Consumer waiting...")
                condition.wait()
                logger.debug("Consumer waiting ended.")
            item = q.pop(0)
            condition.release()

            e = item.run()
            if e is not None:
                condition.acquire()
                q.append(item)  # Put the task back if error occurred.
                condition.release()
            time.sleep(random.random())


if __name__ == '__main__':
    with open('config.json') as f:
        data = json.load(f)
    TOKEN = data["token"]
    g = Github(TOKEN)
    repo = g.get_repo(data["repo"])
    tasks = data["tasks"]
    for task in tasks:
        task["last_success"] = True

    p = ProducerThread()
    c = ConsumerThread()

    p.start()
    c.start()
