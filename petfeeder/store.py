from petfeeder.events import Meal, HealthCheck

from logging import error, debug
import pickle
import os


# This is a Singleton object so that you can load it up anywhere
class Store(object):
    __instance = None

    def __new__(cls, config_file='config.pkl'):
        if cls.__instance is None:
            cls.__instance = super(Store, cls).__new__(cls)
            cls.__instance.__initialize(config_file)
        return cls.__instance

    def __initialize(self, config_file='config.pkl'):
        self.data = {}
        self._config_file = config_file
        self.loaded = False
        self.load()

    def ensure_defaults(self):
        defaults = {
            "timezone": "America/Los_Angeles",
            "scheduled_events": [
                HealthCheck(
                    "7:00 AM",
                    check_id="please-update-this-from-healthchecks.io",
                    name="Daily"
                ),
                Meal("7:00 AM", servings=1, name="Default")
            ]
        }

        if os.getenv("TELEGRAM_API_TOKEN", None) is not None:
            defaults["telegram_api_token"] = os.getenv("TELEGRAM_API_TOKEN")

        if os.getenv("TELEGRAM_BROADCAST_ID", None) is not None:
            defaults["telegram_broadcast_id"] = \
                os.getenv("TELEGRAM_BROADCAST_ID")

        for key, value in defaults.items():
            if key not in self.data:
                debug("Setting default value for: %s" % key)
                self.data[key] = value

    def save(self):
        with open(self._config_file, 'wb') as file:
            pickle.dump(self.data, file)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def unset(self, key):
        del self.data[key]
        self.save()

    def load(self):
        try:
            with open(self._config_file, 'rb') as file:
                self.data = pickle.load(file)
            self.ensure_defaults()
            self.loaded = True
        except Exception as e:
            self.ensure_defaults()
            error("Error loading config file %s. Setting defaults." % str(e))
