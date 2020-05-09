import cherrypy
import json
from petfeeder.scheduler import TimeConverter
from petfeeder import events
import logging


# Dummy webserver for the root entity
class WebServer():
    def __init__(self):
        pass


# TODO: Figure out if there is a more pythonic way to do this
def jsonify_error(status, message, traceback, version):
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': 'Failure', 'status_details': {
        'message': status,
        'description': message
    }})


@cherrypy.tools.json_out()
class APIServer(object):
    exposed = True
    _cp_config = {
        'error_page.400': jsonify_error,
        'error_page.405': jsonify_error,
        'error_page.406': jsonify_error,
        'error_page.411': jsonify_error
    }

    def __init__(self, manager):
        self.endpoints = {
            "event": EventEndpoint(manager),
            "feed": FeedEndpoint(manager)
        }

    def _cp_dispatch(self, vpath):
        if len(vpath) > 0 and vpath[0].lower() == 'event':
            return self.endpoints["event"]

        if len(vpath) > 0 and vpath[0].lower() == 'feed':
            return self.endpoints["feed"]

        return vpath

    def GET(self):
        return '{"msg":"Scheduler"}'


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
class FeedEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager

    def POST(self, servings=1):
        self.manager.action("feed", servings=servings)
        return {"success": True}


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
class EventEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager
        self.endpoints = {
            "meal": MealEndpoint(manager),
            "healthcheck": HealthCheckEndpoint(manager)
        }

    def _cp_dispatch(self, vpath):
        logging.info(vpath)
        if len(vpath) > 0 and vpath[0].lower() == "meal":
            return self.endpoints["meal"]

        if len(vpath) > 0 and vpath[0].lower() == "healthcheck":
            return self.endpoints["healthcheck"]

        return vpath

    def GET(self, event_id=None):
        result = []
        for event in self.manager.get_events():
            if event_id is None or event_id == str(event.id):
                result.append({
                    "type": event.__class__.__name__,
                    "id": str(event.id),
                    "details": event.details()
                })
        return result

    def DELETE(self, event_id=None):
        if event_id is None:
            message = "Invalid path"
            raise cherrypy.HTTPError(406, message=message)

        success = False
        for event in self.manager.get_events():
            if str(event.id) == event_id:
                self.manager.action("remove_event", event=event)
                success = True
                break
        return {"success": success}


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
@cherrypy.popargs("event_id")
class MealEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager

    def GET(self, event_id=None):
        result = []
        for event in self.manager.get_events():
            if event.__class__ != events.Meal:
                continue
            if event_id is None or event_id == str(event.id):
                result.append({
                    "type": event.__class__.__name__,
                    "id": str(event.id),
                    "details": event.details()
                })
        return result

    def PUT(self, event_id=None):
        if event_id is None:
            message = "Must select event to edit"
            raise cherrypy.HTTPError(406, message=message)

        event_to_edit = None
        for event in self.manager.get_events():
            if event.__class__ != events.Meal:
                continue
            if event_id is None or event_id == str(event.id):
                event_to_edit = event
                break

        input_json = cherrypy.request.json

        changes = False
        for key, value in input_json.items():
            if (key.lower() == "time" and value != event_to_edit.time):
                event_to_edit.time = (
                    TimeConverter().sanitize_time_string(value)
                )
                changes = True
                print("%s changed: '%s' to '%s'" % (
                    key, event_to_edit[key.lower()], value)
                )
            if key.lower() == "name" and value != event_to_edit.name:
                event_to_edit.name = value
                changes = True
            if key.lower() == "servings" and value != event_to_edit.servings:
                event_to_edit.servings = value
                changes = True

        if changes:
            self.manager.action("update_event", event=event_to_edit)

        result = {"success": True, "changes": changes}
        return result

    def POST(self, event_id=None):
        if event_id is not None:
            message = "May not create records at subpath"
            raise cherrypy.HTTPError(406, message=message)

        input_json = cherrypy.request.json

        try:
            name = input_json["name"]
            time = input_json["time"]
            servings = input_json["servings"]
        except KeyError as e:
            message = "Missing key: %s" % e
            raise cherrypy.HTTPError(400, message=message)

        event = events.Meal(
            TimeConverter().sanitize_time_string(time),
            servings=servings,
            name=name
        )

        if event:
            self.manager.action("add_event", event=event)
            return {"success": True, "event_id": str(event.id)}
        return {"success": False}


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
@cherrypy.popargs("event_id")
class HealthCheckEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager

    def GET(self, event_id=None):
        result = []
        for event in self.manager.get_events():
            if event.__class__ != events.HealthCheck:
                continue
            if event_id is None or event_id == str(event.id):
                result.append({
                    "type": event.__class__.__name__,
                    "id": str(event.id),
                    "details": event.details()
                })
        return result

    def PUT(self, event_id=None):
        if event_id is None:
            message = "Must select event to edit"
            raise cherrypy.HTTPError(406, message=message)

        event_to_edit = None
        for event in self.manager.get_events():
            if event.__class__ != events.HealthCheck:
                continue
            if event_id is None or event_id == str(event.id):
                event_to_edit = event
                break

        input_json = cherrypy.request.json

        changes = False
        for key, value in input_json.items():
            if (key.lower() == "time" and value != event_to_edit.time):
                event_to_edit.time = (
                    TimeConverter().sanitize_time_string(value)
                )
                changes = True
                print("%s changed: '%s' to '%s'" % (
                    key, event_to_edit[key.lower()], value)
                )
            if key.lower() == "name" and value != event_to_edit.name:
                event_to_edit.name = value
                changes = True
            if key.lower() == "check_id" and value != event_to_edit.check_id:
                event_to_edit.check_id = value
                changes = True

        if changes:
            self.manager.action("update_event", event=event_to_edit)

        result = {"success": True, "changes": changes}
        return result

    def POST(self, event_id=None):
        if event_id is not None:
            message = "May not create records at subpath"
            raise cherrypy.HTTPError(406, message=message)

        input_json = cherrypy.request.json

        try:
            name = input_json["name"]
            time = input_json["time"]
            check_id = input_json["check_id"]

            event = events.HealthCheck(
                TimeConverter().sanitize_time_string(time),
                check_id=check_id,
                name=name
            )
        except KeyError as e:
            message = "Missing key: %s" % e
            raise cherrypy.HTTPError(400, message=message)

        if event:
            self.manager.action("add_event", event=event)
            return {"success": True, "event_id": str(event.id)}
        return {"success": False}
