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
            "event": EventPrimaryEndpoint(manager),
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
class EventPrimaryEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager
        self.endpoints = {
            "meal": MealEndpoint(manager),
            "healthcheck": HealthCheckEndpoint(manager)
        }

    def _cp_dispatch(self, vpath):
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
class EventCRUD(object):
    exposed = True

    def __init__(self, manager, eventClass):
        self.manager = manager
        self._parameters = ['name', 'time']
        self.eventClass = eventClass

    def sanitize(self, key, value):
        # Boilerplate. Raise errors if invalid, otherwise sanitize
        # Implementations should utilize super()
        if key.lower() == "time":
            return TimeConverter().sanitize_time_string(value)
        if key.lower() == "name":
            if len(value) > 64 or len(value) == 0:
                raise Exception(
                    "Invalid length for 'name'. Must be 64 characters or less."
                )
        return value

    def GET(self, event_id=None):
        result = []
        for event in self.manager.get_events():
            if event.__class__ != self.eventClass:
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
            if event.__class__ != self.eventClass:
                continue
            if event_id is None or event_id == str(event.id):
                event_to_edit = event
                break
        if event_to_edit is None:
            message = "Event not found"
            raise cherrypy.HTTPError(400, message=message)

        input_json = cherrypy.request.json

        changes = False
        for key, value in input_json.items():
            for param in self._parameters:
                if key.lower() != param:
                    continue
                try:
                    sanitized_value = self.sanitize(param, value)
                except Exception as e:
                    message = "Invalid value for %s: %s" % (key, str(e))
                    raise cherrypy.HTTPError(400, message=message)

                if sanitized_value != getattr(event_to_edit, param):
                    setattr(event_to_edit, param, sanitized_value)
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

        new_event = {}
        for key, value in input_json.items():
            for param in self._parameters:
                if key.lower() != param:
                    continue
                try:
                    new_event[param] = self.sanitize(param, value)
                except Exception as e:
                    message = "Invalid value for %s: %s" % (key, str(e))
                    raise cherrypy.HTTPError(400, message=message)
        try:
            event = self.eventClass(**new_event)
        except ValueError as e:
            raise cherrypy.HTTPError(400, message=str(e))

        if event:
            self.manager.action("add_event", event=event)
            return {"success": True, "event_id": str(event.id)}
        return {"success": False}


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
@cherrypy.popargs("event_id")
class MealEndpoint(EventCRUD):
    exposed = True

    def __init__(self, manager):
        super().__init__(manager, events.Meal)
        self._parameters += ["servings", "notify"]
        self.manager = manager

    def sanitize(self, key, value):
        if key == "notify":
            return bool(value)
        if key == "servings":
            return int(value)
        return super().sanitize(key, value)


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
@cherrypy.popargs("event_id")
class HealthCheckEndpoint(EventCRUD):
    exposed = True

    def __init__(self, manager):
        super().__init__(manager, events.HealthCheck)
        self._parameters += ["check_id", "notify"]
        self.manager = manager

    def sanitize(self, key, value):
        if key == "notify":
            return bool(value)
        if key == "check_id":
            if len(value) > 128 or len(value) == 0:
                raise Exception(
                    "Invalid length for 'check_id'. Must be between 1 and 64."
                )
            return value
        return super().sanitize(key, value)
