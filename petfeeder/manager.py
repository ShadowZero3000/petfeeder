from petfeeder.mechanical import Feeder
from petfeeder.store import Store
from petfeeder.scheduler import Scheduler
from petfeeder import events
from petfeeder.web import WebServer, APIServer
from petfeeder import integrations

import cherrypy

from logging import info
import os
import sys


def str_to_class(classname):
    return getattr(sys.modules[__name__], classname)


class Manager(object):
    def __init__(self):
        self.store = Store()
        # Raspi pin to listen for reed-switch action on
        listen_pin = self.store.data["settings"]["listen_pin"]
        # Raspi pin to activate to trigger the feeder
        feed_pin = self.store.data["settings"]["feed_pin"]

        self.feeder = Feeder(self, feed_pin, listen_pin)
        self.integrations = {}

        store_integrations = self.store.data.get("integrations")

        for name in integrations.available_integrations():
            integration_class = getattr(
                integrations,
                "%sIntegration" % name.title()
            )
            if name not in store_integrations:
                # Ensure that every integration has a reference
                self.integrations[name] = integration_class(self)
            else:
                self.integrations[name] = integration_class(
                    self, **store_integrations[name])

        self.scheduler = Scheduler(self,
                                   self.store.data.get("scheduled_events"))
        self.web = Web(self)

    def initialize_integrations(self):
        for name, integration in self.integrations.items():
            if integration is not None:
                info("Starting integration: %s" % name)
                integration.start()

    def run(self):
        self.initialize_integrations()
        self.web.start()

    # TODO: Fire off every integration when events occur and let them do their
    #       thing or alternatively have them register with the manager when
    #       there's an action they care about. That would clean up this code
    def action(self, action, **kwargs):
        # Direct commands
        if action == "feed":
            if kwargs.get("notify", False):
                self.integrations["telegram"].message(
                    "Activating feeder for %s - %s times" % (
                        kwargs["name"], str(kwargs["servings"])
                    )
                )

            self.feeder.feed(kwargs["servings"])
            if kwargs.get("notify", False):
                self.action("photo")

        if action == "healthcheck":
            event = kwargs["event"]
            if event.notify:
                self.integrations["telegram"].message(
                    "Activating healthcheck %s" % event.name
                )
            event.run()

        if action == "photo":
            # Take and send a picture afterwards
            # If the integration is disabled, the picture will be None,
            # and sending will do nothing
            picture = self.integrations["camera"].take_picture()
            self.integrations["telegram"].send_photo(picture)

        # Event management
        if action == "add_event":
            info("Adding event %s at %s" % (
                kwargs["event"].name, kwargs["event"].time)
            )
            self.scheduler.add_recurring(kwargs["event"])

        if action == "remove_event":
            self.scheduler.del_recurring(kwargs["event"])

        if action == "update_event":
            self.scheduler.update_recurring(kwargs["event"])

        # Communication
        if action == "warning":
            self.integrations["telegram"].message(
                "WARNING: %s" % kwargs["message"]
            )

        # Integration management
        if action == "save_integrations":
            info("Saving integration settings")
            integration_settings = {}
            for name, integration in self.integrations.items():
                integration_settings[name] = integration.details()
            self.store.set('integrations', integration_settings)

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
                'tools.caching.on': True,
                'tools.expires.secs': 60*60*72  # expire in 3 days
            },
            '/templates': {
                'tools.caching.on': False,
                'tools.staticdir.dir': './public/templates',
                'tools.staticdir.on': True,
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
            'engine.autoreload.on': False,  # Enable for development
            'log.access_file': '',
            'log.error_file': '',
            'log.screen': False,
        })
        cherrypy.server.socket_host = '0.0.0.0'
        cherrypy.server.socket_port = 80

    def start(self):
        cherrypy.engine.start()
        cherrypy.engine.block()
