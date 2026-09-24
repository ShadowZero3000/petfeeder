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

    def toJSON(self):
        return {
            "type": "HealthCheck",
            "id": self.id,
            "name": self.name,
            "time": self.time,
            "check_id": self.check_id
        }


class Meal(object):
    def __init__(self, time_string, servings, name, blah):
        self.id = str(uuid.uuid1())
        print("New object created")
        self.servings = servings
        self.time = time_string
        self.name = name
        self.blah = blah

    def __getitem__(cls, x):
        return getattr(cls, x)

    def details(self):
        return {
            "name": self.name,
            "time": self.time,
            "servings": self.servings
        }

    def toJSON(self):
        return {
            "id": self.id,
            "name": self.name,
            "time": self.time,
            "servings": self.servings,
            "blah": self.blah
        }

    def __setstate__(self, d):
        for k in ['time','name','servings', 'blah']:
            try:
                setattr(self, k, d[k])
            except KeyError:
                # Missing a key that's in a newer version of this thing
                setattr(self, k, None)

        self.id = d["id"]

    def __getstate__(self):
        return self.toJSON()

import json
from json import JSONEncoder
import jsonpickle
import pickle

# class EventEncoder(JSONEncoder):
#     def default(self, o):
#         return o.toJSON()

m=Meal("7:00", 3, "Test", "hi")

# encoded = json.dumps(m, cls=EventEncoder)
# print(m)
# print(encoded)
# print("---")
# decoded = json.loads(encoded)
# print(decoded)
# print(decoded.toJSON())
# encoded_pickle = jsonpickle.encode(m, unpicklable=True)
# print(encoded_pickle)
# decoded=jsonpickle.decode(encoded_pickle)
# print(decoded)
# print(decoded.toJSON())

# with open('test.pkl', 'wb') as file:
#     pickle.dump(m, file)

# decoded=None
# with open('test.pkl', 'r') as file:
#     decoded=jsonpickle.decode(file.read(), reset=True)
# print(decoded)
# print(decoded.toJSON())

with open('test.pkl', 'rb') as file:
    result=pickle.load(file)

print(result)
print(result.toJSON())
