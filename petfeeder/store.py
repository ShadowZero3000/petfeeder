from petfeeder.events import Meal, HealthCheck
import jsonpickle

from logging import error, debug, info
import pickle


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
            ],
            "integrations": {},
            "settings": {
                "listen_pin": 13,
                "feed_pin": 11
            }
        }

        for key, value in defaults.items():
            if key not in self.data:
                debug("Setting default value for: %s" % key)
                self.data[key] = value

    def save(self):
        with open(self._config_file, 'w') as file:
            encoded_pickle = jsonpickle.encode(self.data, unpicklable=True)
            file.write(encoded_pickle)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def unset(self, key):
        del self.data[key]
        self.save()

    def load(self):
        loaded = False
        try:
            with open(self._config_file, 'r') as file:
                self.data = jsonpickle.decode(file.read(), keys=True)
            loaded = True
        except Exception as e:
            info("Failed to load new style pickle: %s" % str(e))
        if not loaded:
            try:
                with open(self._config_file, 'rb') as file:
                    old_data = pickle.load(file)
                # Convert format to the new one
                encoded_pickle = jsonpickle.encode(old_data, unpicklable=True)
                self.data = jsonpickle.decode(encoded_pickle, reset=False)

                loaded = True
                self.save()  # Ensure we save in the updated format
            except Exception as e:
                info("Failed to load old style pickle: %s" % str(e))
        self.ensure_defaults()
        if not loaded:
            error("Error loading config file %s. Setting defaults." %
                  self._config_file)
            self.save()  # Ensure we create the default file
        self.loaded = True
