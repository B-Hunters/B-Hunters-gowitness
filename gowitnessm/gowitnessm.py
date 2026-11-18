from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
import tempfile
import requests
import re
import glob
from bson.objectid import ObjectId

#: The parts of a gowitness record worth keeping.
#:
#: The record carries the body of the page, the cookie jar and the
#: network log.  The body is the interesting part of a scan and the
#: least interesting part of a report: it is large, it is the page the
#: target serves to an anonymous visitor, and the cookies in it are
#: the target's own session - which does not belong in a database
#: that every later scan reads back.
KEPT_FIELDS = (
    "id",
    "url",
    "final_url",
    "response_code",
    "response_reason",
    "content_length",
    "title",
    "perception_hash",
    "perception_hash_group_id",
    "is_pdf",
    "failed",
    "failed_reason",
    "tls",
    "technologies",
    "screenshot",
    "file_name",
    "time",
)

#: The parts that are dropped.
DROPPED_FIELDS = ("html", "cookies", "network", "console")


def trim_record(record):
    """The part of a gowitness record that is worth keeping."""
    if not isinstance(record, dict):
        return {}
    kept = {key: value for key, value in record.items() if key in KEPT_FIELDS}
    for field in DROPPED_FIELDS:
        kept.pop(field, None)
    headers = kept.get("headers")
    if isinstance(headers, list):
        # A Set-Cookie header is the target's session, in the response.
        kept["headers"] = [
            header
            for header in headers
            if str(header.get("key", "")).strip().lower() != "set-cookie"
        ]
    return kept


def trim_records(payload):
    """The gowitness output, without the bodies and the cookies."""
    if isinstance(payload, list):
        return [trim_record(record) for record in payload]
    return trim_record(payload)


class gowitnessm(BHunters):
    """
    B-Hunters Gowitness developed by Bormaa
    """

    identity = "B-Hunters-GoWitness"
    version = __version__
    persistent = True
    filters = [
        {
            "type": "subdomain", "stage": "new"
        }
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
    def getscreenshot(self,url):
        try:
            jsonoutput=self.generate_random_filename()
            screenshotdir=self.generate_random_filename()
            output=subprocess.run(["gowitness", "scan", "single", "-u", url, "-s", screenshotdir, "--write-jsonl", "--write-jsonl-file", jsonoutput], capture_output=True, text=True)
            screenshot_data=""
            json_data={}
            file_list = glob.glob(f"{screenshotdir}/*")
            for file_path in file_list:
                with open(file_path, "rb") as file:
                    screenshot_data = file.read()
            with open(jsonoutput, "r") as file:
                json_data = json.load(file)
        except Exception as e:
            self.log.error(e)
        return screenshot_data,json_data
                
    def scan(self,url):

        return self.getscreenshot(url)

        
    def process(self, task: Task) -> None:
        source = task.payload["source"]
        subdomain = task.payload["subdomain"]
        subdomain = re.sub(r'^https?://', '', subdomain)
        subdomain = subdomain.rstrip('/')
        scan_id = task.payload_persistent["scan_id"]
        report_id=task.payload_persistent["report_id"]
        url = task.payload["data"]
        self.log.info("Starting processing new url " +url)
        self.update_task_status(subdomain,"Started")
        url = re.sub(r'^https?://', '', url)
        url = url.rstrip('/')
        try:
            screenshot,jsondata=self.scan(task.payload["data"])
            self.waitformongo()
            db = self.db
            collection = db["reports"]

            domain_document = collection.find_one({"_id": ObjectId(report_id)})
            if domain_document:
                # The record is trimmed before it is stored: the body of
                # the page and the target's cookies are not the report.
                stored = trim_records(jsondata)
                if "data" in domain_document and "gowitness" in domain_document["data"]:
                    collection.update_one({"_id": ObjectId(report_id)}, {"$push": {"data.gowitness": stored}})
                else:
                    collection.update_one({"_id": ObjectId(report_id)}, {"$set": {"data.gowitness": stored}})
                collection.update_one({"_id": ObjectId(report_id)}, {"$set": {"Screenshot": screenshot}})
            self.update_task_status(subdomain,"Finished")
        except Exception as e:
            self.update_task_status(subdomain,"Failed")
            self.log.error(e)