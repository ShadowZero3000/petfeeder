from petfeeder.mechanical import initialize_feeder
from petfeeder.store import Store
from petfeeder.scheduler import Scheduler, TimeConverter
from petfeeder import events
from petfeeder.telegram import Telegram
from petfeeder.web import WebServer, APIServer

import cherrypy

from logging import info
import os


class Manager(object):
    def __init__(self):
        self.store = Store()
        # Raspi pin to listen for reed-switch action on
        listen_pin = int(os.getenv('LISTEN_PIN') or 12)
        # Raspi pin to activate to trigger the feeder
        feed_pin = int(os.getenv('FEED_PIN') or 11)

        self.feeder = initialize_feeder(self, listen_pin, feed_pin)

        # TODO: Split this out into its own thing so we can have multiple
        self.chat = Chat(self)

        self.scheduler = Scheduler(self,
                                   self.store.data.get("scheduled_events"))
        self.web = Web(self)

    def run(self):
        self.chat.start()
        self.web.start()

    def action(self, action, **kwargs):
        if action == "feed":
            if kwargs.get("notify", False):
                self.chat.message(
                    "Activating feeder for %s - %s times" % (
                        kwargs["name"], str(kwargs["servings"])
                    )
                )
            self.feeder.feed(kwargs["servings"])

        if action == "add_event":
            info("Adding event %s at %s" % (
                kwargs["event"].name, kwargs["event"].time)
            )
            self.scheduler.add_recurring(kwargs["event"])

        if action == "remove_event":
            self.scheduler.del_recurring(kwargs["event"])

        if action == "update_event":
            self.scheduler.update_recurring(kwargs["event"])

        if action == "warning":
            self.chat.message(
                "WARNING: %s" % kwargs["message"]
            )

        if action == "healthcheck":
            event = kwargs["event"]
            if event.notify:
                self.chat.message("Activating healthcheck %s" % event.name)
            event.run()

    def handle_event(self, event):
        if event.__class__ == events.Meal:
            self.action("feed", **event.details())

        if event.__class__ == events.HealthCheck:
            self.action("healthcheck", **{"event": event})

    def get_events(self):
        return self.scheduler.scheduled_events


class Web():
    def __init__(self, manager):
        self.manager = manager

        cherrypy.tree.mount(WebServer(), '/', {
            '/': {
                'tools.response_headers.on': True,
                'tools.sessions.on': True,
                'tools.staticdir.dir': './public',
                'tools.staticdir.index': 'index.html',
                'tools.staticdir.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd()),
                'tools.trailing_slash.on': False,
            }
        })

        cherrypy.tree.mount(APIServer(manager), '/api', {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.json_out.on': True,
                'tools.trailing_slash.on': False,
            }
        })

        cherrypy.config.update({
            # 'engine.autoreload.on': False,  # Enable for development
            'log.access_file': '',
            'log.error_file': '',
            'log.screen': False,
        })
        cherrypy.server.socket_host = '0.0.0.0'
        cherrypy.server.socket_port = 80

    def start(self):
        cherrypy.engine.start()
        cherrypy.engine.block()


class Chat():
    def __init__(self, manager):
        self.manager = manager

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

        store = Store()
        api_key = store.data.get("telegram_api_token", None)
        broadcast_id = store.data.get("telegram_broadcast_id", None)

        self.enabled = False
        if api_key is not None and broadcast_id is not None:
            self.enabled = True

        if self.enabled:
            self.telegram = Telegram(api_key, broadcast_id)

    def message(self, message):
        if not self.enabled:
            return

        self.telegram.message(message)

    def start(self):
        if not self.enabled:
            info("Telegram integration not enabled")
            return

        bot = self.telegram.bot

        @bot.message_handler(commands=['help'])
        @bot.channel_post_handler(commands=['help'])
        def bot_help(message):
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

        @bot.message_handler(commands=['feed'],
                             regexp='^/[a-z]+ [0-9]+$')
        @bot.channel_post_handler(commands=['start', 'feed'],
                                  regexp='^/[a-z]+ [0-9]+$')
        def bot_feed_request(message):
            servings = int(message.text.split(" ")[1])

            self.telegram.respond(message, "Acknowledged")
            self.manager.action("feed", servings=servings)

        @bot.message_handler(commands=['schedule'], regexp='^/schedule .*$')
        @bot.channel_post_handler(commands=['schedule'],
                                  regexp='^/schedule .*$')
        def bot_schedule_show(message):
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
