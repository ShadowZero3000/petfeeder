import urllib.request
from logging import info, warn

import uuid


class Event(object):
    _parameters = ["name", "time"]
    _defaults = {}

    def __init__(self, name, time):
        self.id = str(uuid.uuid1())
        self._defaults = {}
        self.name = name
        self.time = time

    def __getitem__(cls, x):
        return getattr(cls, x)

    def details(self):
        result = {}
        for key in self._parameters:
            result[key] = getattr(self, key)
        return result

    def toJSON(self):
        result = self.details()
        result["id"] = self.id
        return result

    def ensure_all_attributes(self):
        for key, value in self._defaults.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def __setstate__(self, d):
        for k in self._parameters:
            try:
                setattr(self, k, d[k])
            except KeyError:
                # Missing a key that's in a newer version of this thing
                setattr(self, k, None)

        self.id = d["id"]

    def __getstate__(self):
        self.ensure_all_attributes()
        return self.toJSON()


class HealthCheck(Event):
    _parameters = Event._parameters + ['check_id', 'notify']
    _defaults = {
        "notify": False
    }

    def __init__(self, time, check_id, name, notify=False):
        super().__init__(name, time)

        self.check_id = check_id
        self.notify = notify

    def run(self):
        info("Healthcheck started")
        try:
            urllib.request.urlopen(
                "https://hc-ping.com/%s" % self.check_id,
                None, 2
            )
        except Exception as e:
            warn("Failed to submit healthcheck: %s" % e)


class Meal(Event):
    _parameters = Event._parameters + ['servings', 'notify']
    _defaults = {
        "notify": False
    }

    def __init__(self, time, servings, name, notify=False):
        super().__init__(name, time)

        self.servings = servings
        self.notify = notify
