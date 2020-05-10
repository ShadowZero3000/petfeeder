import urllib.request
from logging import info, warn

import uuid


class HealthCheck(object):
    def __init__(self, time_string, check_id, name):
        self.id = str(uuid.uuid1())
        self.check_id = check_id
        self.time = time_string
        self.name = name

    def __getitem__(cls, x):
        return getattr(cls, x)

    def run(self):
        info("Healthcheck started")
        try:
            urllib.request.urlopen("https://hc-ping.com/%s" % self.check_id)
        except Exception as e:
            warn("Failed to submit healthcheck: %s" % e)

    def details(self):
        return {
            "name": self.name,
            "time": self.time,
            "service": "healthchecks.io",
            "check_id": self.check_id
        }


class Meal(object):
    def __init__(self, time_string, servings, name):
        self.id = str(uuid.uuid1())

        self.servings = servings
        self.time = time_string
        self.name = name

    def __getitem__(cls, x):
        return getattr(cls, x)

    def details(self):
        return {
            "name": self.name,
            "time": self.time,
            "servings": self.servings
        }
