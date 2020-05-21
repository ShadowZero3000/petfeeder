from logging import info
from time import sleep
import re
import picamera

from petfeeder import events
from petfeeder.telegram import Telegram
from petfeeder.scheduler import TimeConverter


def available_integrations():
    return {
        "telegram": TelegramIntegration,
        "camera": CameraIntegration,
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

    def send_photo(self, filename):
        if not self.enabled or filename is None:
            return

        self.telegram.send_photo(filename)

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

    def take_picture(self):
        if not self.enabled:
            return

        # Using with here causes the camera object to get closed out properly
        with picamera.PiCamera() as camera:
            camera.resolution = (1024, 768)
            camera.start_preview()
            # Camera warm-up time
            sleep(2)
            camera.capture('still.jpg')

        return 'still.jpg'
