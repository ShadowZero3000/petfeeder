import RPi.GPIO as GPIO  # Import Raspberry Pi GPIO library
from datetime import datetime
from logging import info, error
from time import sleep
import os
import re
import picamera

from petfeeder import events
from petfeeder.telegram import Telegram
from petfeeder.scheduler import TimeConverter


def available_integrations():
    return {
        "telegram": TelegramIntegration,
        "camera": CameraIntegration,
        "food_check": FoodCheckIntegration,
    }


class TelegramIntegration():
    # TODO: Maybe move this to a function?
    parameters = ['enabled', 'api_key', 'broadcast_id', 'login_password']

    def __init__(self, manager, **kwargs):
        self.manager = manager

        self.api_key = kwargs.get('api_key', None)
        self.broadcast_id = kwargs.get('broadcast_id', None)
        self.enabled = kwargs.get('enabled', False)
        self.login_password = kwargs.get('login_password', "No password set")
        self.authenticated_users = kwargs.get('authenticated_users', [])

        self.commands = {
            "help": {
                "description": "This help message"
            },
            "feed": {
                "description":
                    "Start a feeding. Takes one argument: # of feedings"
            },
            "schedule": {
                "description":
                    "Lets you manage the scheduler. \n \
                    Event types: meal|healthcheck\nTry /help schedule",
                "add": {
                    "description": "Adds events. Input: HH:MM #\n\
                       Try: /schedule add meal 8:00 4"
                },
                "remove": {
                    "description": "Removes events. \n\
                        Input: ID of event to remove (See /schedule show)"
                },
                "show": {
                    "description": "Shows currently scheduled mealtimes. \
                        Use the IDs for removal."
                }
            }
        }

    def details(self):
        return {
            'api_key': self.api_key,
            'broadcast_id': self.broadcast_id,
            'enabled': self.enabled,
            'login_password': self.login_password,
            'authenticated_users': self.authenticated_users
        }

    def web_details(self):
        return {
            'api_key': {
                'name': 'API Key',
                'description':
                    "Key used for authenticating to Telegram's service",
                'value': self.api_key
            },
            'broadcast_id': {
                'name': 'Broadcast Channel ID',
                'description':
                    'Channel ID for sending messages when events occur',
                'value': self.broadcast_id
            },
            'enabled': {
                'name': 'Enabled',
                'description': 'Whether this integration should be used',
                'type': 'bool',
                'value': self.enabled
            },
            'login_password': {
                'name': 'Login password',
                'description': 'The password users must give, along with /login, to use this bot',
                'value': self.login_password,
                'type': 'password'
            }
        }

    def reconfigure(self, details):
        changes = False
        if details.get("api_key") and details["api_key"] != self.api_key:
            changes = True
            self.api_key = details["api_key"]

        if details.get("broadcast_id") \
                and details["broadcast_id"] != self.broadcast_id:

            changes = True
            self.broadcast_id = details["broadcast_id"]

        if details.get("enabled") is not None \
                and details["enabled"] != self.enabled:

            changes = True
            self.enabled = details["enabled"]

        if details.get("login_password") is not None \
                and details["login_password"] != self.login_password:

            changes = True
            self.login_password = details["login_password"]

        if changes:
            info("Reconfiguring Telegram Integration")
            self.stop()
            self.start()
            self.manager.action("save_integrations")

    def stop(self):
        if hasattr(self, 'telegram'):
            self.telegram.stop()
            self.telegram.join()
            del self.telegram
            info("Telegram bot stopped")

    @staticmethod
    def sanitize(key, value):
        if key == 'api_key':
            if re.match(r'^[0-9]+:[A-z0-9_-]{35}$', value) is None:
                raise Exception('Invalid Telegram api_key value.')
            return str(value)

        if key == 'broadcast_id':
            if re.match(r'^-?[0-9]*$', value) is None:
                raise Exception('Invalid Telegram broadcast_id value.')
            return int(value)

        if key == 'enabled':
            return bool(value)

        if key == 'login_password':
            if re.match(r'^[A-z0-9_ -]+$', value) is None:
                raise Exception('Invalid Telegram login_password value.')
            return str(value)

        raise Exception('Invalid key for Telegram integration: %s' % key)

    def message(self, message):
        if not self.enabled:
            return

        self.telegram.message(message)

    def send_photo(self, filename, caption=None):
        if not self.enabled or filename is None:
            return

        self.telegram.send_photo(filename, caption=caption)

    def start(self):
        if not self.enabled:
            info("Telegram integration not enabled")
            return

        info("Telegram integration starting")
        self.telegram = Telegram(self.api_key, self.broadcast_id)
        bot = self.telegram.bot

        @bot.channel_post_handler(commands=['help'])
        def bot_channel_help(message):
            self.telegram.respond(message, "Try asking in a direct message")

        @bot.message_handler(commands=['help'])
        def bot_help(message):
            info("Got message help")
            args = message.text.split(" ")

            if len(args) == 1:
                help_text = "The following commands are available: \n"
                for key in self.commands:
                    help_text += "/%s: %s\n" % (
                        key,
                        self.commands[key]["description"]
                    )
            else:
                help_text = "Help for: /%s \n" % args[1]
                for key in self.commands[args[1]]:
                    if key == "description":
                        continue
                    help_text += "/%s %s: %s\n" % (
                        args[1],
                        key,
                        self.commands[args[1]][key]["description"]
                    )
            self.telegram.respond(message, help_text)

        @bot.message_handler(commands=['authenicate', 'login', 'start'],
                             regexp='^/[^ ]+ [A-z0-9 _-]+$')
        def bot_auth_request(message):
            self.telegram.respond(message, "Checking your password...")
            password = " ".join(message.text.split(" ")[1:])
            if password == self.login_password:
                self.authenticated_users.append(message.chat.id)
                self.manager.action("save_integrations")
                self.telegram.respond(
                    message, 'Acknowledged. You may now give me commands.')

        @bot.message_handler(commands=['feed'],
                             regexp='^/[a-z]+ [0-9]+$')
        def bot_feed_request(message):
            if message.chat.id not in self.authenticated_users:
                return

            servings = int(message.text.split(" ")[1])

            self.telegram.respond(message, "Acknowledged")
            self.manager.action("feed", servings=servings)

        @bot.message_handler(commands=['schedule'], regexp='^/schedule .*$')
        def bot_schedule_show(message):
            if message.chat.id not in self.authenticated_users:
                return

            args = message.text.split(" ")

            if(args[1] == "show"):
                self.telegram.respond(message, "My schedules:")

                result = ""
                for idx, event in enumerate(
                        self.manager.scheduler.scheduled_events):
                    if type(event) == events.Meal:
                        result += "%s: %s - %s servings at %s\n" % (
                            idx, event.name, event.servings, event.time
                        )
                    if type(event) == events.HealthCheck:
                        result += "%s: %s - HealthCheck at %s\n" % (
                            idx, event.name, event.time
                        )

                self.telegram.respond(message, result)

            if(args[1] == "add"):
                event = self.args_to_event(args[2:])
                self.manager.action("add_event", event=event)
                self.telegram.respond(message, "Added new %s: %s at %s" % (
                    event.__class__.__name__, event.name, event.time)
                )

            if(args[1] == "remove"):
                event = self.find_event_by_index(args[2])
                self.manager.action(
                    "remove_event",
                    event=event,
                    message=message
                )
                self.telegram.respond(message, "Removed.")

    def args_to_event(self, args):
        tc = TimeConverter()
        if(args[0] == "meal"):
            time = tc.sanitize_time_string(args[1])
            servings = int(args[2])
            name = " ".join(args[3:])
            return events.Meal(time, servings=servings, name=name)

        if(args[0] == "healthcheck"):
            time = tc.sanitize_time_string(args[1])
            check_id = args[2]
            name = " ".join(args[3:])
            return events.HealthCheck(time, check_id=check_id, name=name)

    def find_event_by_index(self, event_index):
        for idx, event in enumerate(self.manager.scheduler.scheduled_events):
            if idx == int(event_index):
                return event


class CameraIntegration:

    # TODO: Maybe move this to a function?
    parameters = ['enabled']

    def __init__(self, manager, **kwargs):
        self.manager = manager

        self.enabled = kwargs.get('enabled', False)
        self.light_pin = kwargs.get('light_pin', 15)
        GPIO.setup(self.light_pin, GPIO.OUT, initial=GPIO.LOW)

    def details(self):
        return {
            'enabled': self.enabled
        }

    def web_details(self):
        return {
            'enabled': {
                'name': 'Enabled',
                'description': 'Whether this integration should be used',
                'type': 'bool',
                'value': self.enabled
            }
        }

    def reconfigure(self, details):
        changes = False
        if details.get("enabled") is not None \
                and details["enabled"] != self.enabled:

            changes = True
            self.enabled = details["enabled"]

        if changes:
            info("Reconfiguring Camera Integration")
            # No actions necessary, enabled flag is all that matters
            self.manager.action("save_integrations")

    @staticmethod
    def sanitize(key, value):
        if key == 'enabled':
            return bool(value)

        raise Exception('Invalid key for Camera integration: %s' % key)

    def start(self):
        if not self.enabled:
            info("Camera integration not enabled")
            return

        info("Camera integration is available")
        # Nothing to do

    def take_picture(self, filename='public/media/still.jpg'):
        if not self.enabled:
            return

        GPIO.output(self.light_pin, GPIO.HIGH)
        try:
            # Using with here causes the camera object to get closed out properly
            with picamera.PiCamera() as camera:
                camera.resolution = (640, 480)
                camera.start_preview()
                # Camera warm-up time
                sleep(2)
                camera.capture(filename, format='jpeg')
        except picamera.exc.PiCameraError as e:
            error("Error taking picture: %s" % str(e))
            return None
        finally:
            # Always turn the light back off, even if the camera failed
            GPIO.output(self.light_pin, GPIO.LOW)

        return filename


class FoodCheckIntegration:
    """
    Compares photos taken before and after a feeding to catch an empty or
    jammed hopper. Needs the camera integration enabled too.
    """

    # TODO: Maybe move this to a function?
    parameters = ['enabled', 'log_only', 'threshold', 'pixel_delta',
                  'max_captures']

    capture_dir = 'captures'

    def __init__(self, manager, **kwargs):
        self.manager = manager

        self.enabled = kwargs.get('enabled', False)
        self.log_only = kwargs.get('log_only', True)
        self.threshold = kwargs.get('threshold', 0.02)
        self.pixel_delta = kwargs.get('pixel_delta', 25)
        self.max_captures = kwargs.get('max_captures', 200)

    def details(self):
        return {
            'enabled': self.enabled,
            'log_only': self.log_only,
            'threshold': self.threshold,
            'pixel_delta': self.pixel_delta,
            'max_captures': self.max_captures
        }

    def web_details(self):
        return {
            'enabled': {
                'name': 'Enabled',
                'description':
                    'Whether this integration should be used. '
                    'Requires the camera integration',
                'type': 'bool',
                'value': self.enabled
            },
            'log_only': {
                'name': 'Log only',
                'description':
                    'Report the change score, but never send the '
                    'empty hopper warning',
                'type': 'bool',
                'value': self.log_only
            },
            'threshold': {
                'name': 'Threshold',
                'description':
                    'Warn when less than this fraction of the photo '
                    'changes after feeding (0.02 = 2%)',
                'value': self.threshold
            },
            'pixel_delta': {
                'name': 'Pixel delta',
                'description':
                    'How much a pixel must change (0-255) to count '
                    'as changed',
                'value': self.pixel_delta
            },
            'max_captures': {
                'name': 'Max captures',
                'description':
                    'Number of before/after photo pairs to keep in %s/'
                    % self.capture_dir,
                'value': self.max_captures
            }
        }

    def reconfigure(self, details):
        changes = False
        for key in self.parameters:
            if details.get(key) is not None \
                    and details[key] != getattr(self, key):

                changes = True
                setattr(self, key, details[key])

        if changes:
            info("Reconfiguring Food Check Integration")
            # No actions necessary, the settings are read on every feeding
            self.manager.action("save_integrations")

    @staticmethod
    def sanitize(key, value):
        if key in ['enabled', 'log_only']:
            return bool(value)

        if key == 'threshold':
            try:
                value = float(value)
            except ValueError:
                raise Exception('Invalid Food Check threshold value.')
            if not 0 <= value <= 1:
                raise Exception('Food Check threshold must be 0 to 1.')
            return value

        if key == 'pixel_delta':
            if re.match(r'^[0-9]+$', str(value)) is None \
                    or not 1 <= int(value) <= 255:
                raise Exception('Food Check pixel_delta must be 1 to 255.')
            return int(value)

        if key == 'max_captures':
            if re.match(r'^[0-9]+$', str(value)) is None \
                    or int(value) < 1:
                raise Exception('Food Check max_captures must be 1 or more.')
            return int(value)

        raise Exception('Invalid key for Food Check integration: %s' % key)

    def start(self):
        if not self.enabled:
            info("Food check integration not enabled")
            return

        info("Food check integration is available")
        # Nothing to do

    def new_capture(self):
        # Timestamp shared by a before/after pair. Sorts oldest to newest.
        os.makedirs(self.capture_dir, exist_ok=True)
        return datetime.now().strftime('%Y-%m-%dT%H-%M-%S')

    def capture_path(self, stamp, label):
        return os.path.join(self.capture_dir, '%s_%s.jpg' % (stamp, label))

    def check(self, stamp, before, after):
        """
        Scores a before/after pair, adds the score to their filenames and
        prunes old captures. Returns (score, renamed after path)
        """
        # Imported here so a missing numpy/Pillow only breaks the check,
        # never the feeder itself
        from petfeeder.vision import change_score

        score = change_score(before, after, pixel_delta=self.pixel_delta)
        info("Food check change score: %.4f (threshold %s)" % (
            score, self.threshold))

        for label, path in [('before', before), ('after', after)]:
            scored = self.capture_path(
                stamp, 'score%.3f_%s' % (score, label))
            os.rename(path, scored)
        self.prune_captures()

        return score, self.capture_path(stamp, 'score%.3f_after' % score)

    def food_missing(self, score):
        return not self.log_only and score < self.threshold

    def prune_captures(self):
        files = sorted(os.listdir(self.capture_dir))
        # Every file in a pair starts with the same timestamp
        stamps = sorted(set(name.split('_')[0] for name in files))
        old_stamps = set(stamps[:-self.max_captures])
        for name in files:
            if name.split('_')[0] in old_stamps:
                os.remove(os.path.join(self.capture_dir, name))
