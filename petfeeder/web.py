import cherrypy
import json
from petfeeder.scheduler import TimeConverter
from petfeeder import events
from petfeeder import integrations


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
        'error_page.411': jsonify_error,
        'error_page.415': jsonify_error
    }

    def __init__(self, manager):
        self.endpoints = {
            "event": EventPrimaryEndpoint(manager),
            "feed": FeedEndpoint(manager),
            "integration": IntegrationEndpoint(manager),
            "photo": PhotoEndpoint(manager),
        }

    def _cp_dispatch(self, vpath):
        for name, endpoint in self.endpoints.items():
            if len(vpath) > 0 and vpath[0].lower() == name:
                return endpoint

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
class PhotoEndpoint(object):
    exposed = True

    def __init__(self, manager):
        self.manager = manager

    def POST(self):
        self.manager.action("photo")
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


@cherrypy.tools.json_in()
@cherrypy.tools.json_out()
@cherrypy.popargs("integration_name")
class IntegrationEndpoint():
    exposed = True

    def __init__(self, manager):
        self.manager = manager

    def GET(self, integration_name=None):
        result = []
        for name, integration_class in \
                integrations.available_integrations().items():

            if integration_name is None or integration_name == name:
                integration = {
                    "name": name,
                    "parameters": integration_class.parameters,
                    "enabled": name in self.manager.integrations
                }
                if integration["enabled"]:
                    integration["details"] = \
                        self.manager.integrations[name].web_details()
                result.append(integration)
        return result

    def PUT(self, integration_name=None):
        if integration_name is None:
            message = "Must select integration to edit"
            raise cherrypy.HTTPError(406, message=message)

        integration_name = integration_name.lower()

        available_integrations = integrations.available_integrations()
        if integration_name not in available_integrations:
            message = "Integration not available"
            raise cherrypy.HTTPError(406, message=message)

        input_json = cherrypy.request.json

        requested_details = {}

        changes = False
        for key, value in input_json.items():
            for param in available_integrations[integration_name].parameters:
                if key.lower() != param:
                    continue
                try:
                    # Class method on the integration to sanitize values
                    requested_details[key] = \
                        available_integrations[integration_name]\
                        .sanitize(param, value)
                except Exception as e:
                    message = "Error updating %s: %s" % (key, str(e))
                    raise cherrypy.HTTPError(400, message=message)
        # Consider making this a manager action instead of a direct call
        # The integration is enabled
        self.manager.integrations[integration_name].reconfigure(
            requested_details)

        result = {"success": True, "changes": changes}
        return result

# TODO: Settings endpoint so you can adjust timezone
# But....that's a lot of effort for how much time I want to devote to it
