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
        url = task.payload["data"]
        self.log.info("Starting processing new url " +url)
        self.update_task_status(subdomain,"Started")
        url = re.sub(r'^https?://', '', url)
        url = url.rstrip('/')
        try:
            db = self.db
            collection = db["domains"]

            screenshot,jsondata=self.scan(task.payload["data"])
            domain_document = collection.find_one({"Domain": subdomain})
            if domain_document:
                if "data" in domain_document and "gowitness" in domain_document["data"]:
                    collection.update_one({"Domain": subdomain}, {"$push": {"data.gowitness": jsondata}})
                else:
                    collection.update_one({"Domain": subdomain}, {"$set": {"data.gowitness": jsondata}})
                collection.update_one({"Domain": subdomain}, {"$set": {"Screenshot": screenshot}})
            self.update_task_status(subdomain,"Finished")
        except Exception as e:
            self.update_task_status(subdomain,"Failed")
            self.log.error(e)