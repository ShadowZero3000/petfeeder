import schedule
import pytz
import pendulum
from logging import info, debug
import threading  # Allow for threading

from time import sleep
import re

from petfeeder.events import Meal, HealthCheck
from petfeeder.store import Store


class Scheduler(threading.Thread):
    def __init__(self, manager, scheduled_events):
        threading.Thread.__init__(self)
        self.daemon = True

        self.manager = manager
        self.scheduled_events = scheduled_events
        self._store = Store()

        self.start()

    def run(self):
        info("Scheduling events from config")
        for event in self.scheduled_events:
            if type(event) == Meal:
                info("Added Meal: %s - %s" % (event.name, event.time))
                self._add_recurring_to_scheduler(event)
            if type(event) == HealthCheck:
                info("Added HealthCheck: %s - %s" % (event.name, event.time))
                self._add_recurring_to_scheduler(event)

        debug("Currently scheduled jobs: %s" % schedule.jobs)
        while True:
            schedule.run_pending()
            sleep(1)

    def _add_recurring_to_scheduler(self, event):
        timestring = TimeConverter().local_string_to_utc_string(event.time)
        schedule.every().day.at(timestring).do(
            self.manager.handle_event, event
        ).tag(event.id)

    def add_recurring(self, event):
        self.scheduled_events.append(event)
        self._add_recurring_to_scheduler(event)
        self._store.set("scheduled_events", self.scheduled_events)

    def del_recurring(self, event):
        info("Removing job: %s" % event)
        schedule.clear(event.id)
        self.scheduled_events.remove(event)
        self._store.set("scheduled_events", self.scheduled_events)
        debug("Currently scheduled jobs: %s" % schedule.jobs)

    def update_recurring(self, event):
        # The event itself has already been changed, just tell the scheduler
        info("Updating job: %s" % event)
        schedule.clear(event.id)
        self._add_recurring_to_scheduler(event)

        self._store.set("scheduled_events", self.scheduled_events)
        debug("Currently scheduled jobs: %s" % schedule.jobs)

    def get_event(self, needle):
        for event in self.scheduled_events:
            if event.id == needle.id:
                return event
        return None


class TimeConverter():
    def __init__(self):
        self._store = Store()
        timezone_string = self._store.data.get("timezone")
        self.tz_string = timezone_string
        self.tz = pytz.timezone(self.tz_string)

    def time_string_to_timestamp(self, time_string):
        while True:  # Allows for short circuiting
            # timestamp with AM/PM
            match = re.match(r"\d{1,2}:\d{2} [AaPp][Mm]", time_string)
            if match:
                timestamp = pendulum.from_format(time_string, 'h:mm A')
                break

            # full time with milliseconds
            match = re.match(r"\d{1,2}:\d{2}:\d{2}\.\d+", time_string)
            if match:
                timestamp = pendulum.from_format(time_string, 'H:mm:ss.S')
                break

            # timestamp missing milliseconds
            match = re.match(r"\d{1,2}:\d{2}:\d{2}", time_string)
            if match:
                timestamp = pendulum.from_format(time_string, 'H:mm:ss')
                break

            # timestamp military hours and minutes
            match = re.match(r"\d{1,2}:\d{2}", time_string)
            if match:
                timestamp = pendulum.from_format(time_string, 'H:mm')
                break

            # unknown timestamp format
            raise Exception("Invalid time string")
        info(timestamp)
        return timestamp.replace(tzinfo=self.tz).astimezone(pytz.utc)

    def timestamp_to_local_string(self, timestamp, fmt="%-I:%M %p"):
        return timestamp.astimezone(self.tz).time().strftime(fmt)

    def timestamp_to_utc_string(self, timestamp):
        return timestamp.time().strftime("%H:%M")

    def local_string_to_utc_string(self, time_string):
        return self.timestamp_to_utc_string(
            self.time_string_to_timestamp(time_string)
        )

    def sanitize_time_string(self, time_string):
        timestamp = self.time_string_to_timestamp(time_string)
        return self.timestamp_to_local_string(timestamp)
