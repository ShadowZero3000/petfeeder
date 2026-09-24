import telebot

from logging import error
from time import sleep

import threading


class Telegram(threading.Thread):
    def __init__(self, api_token, broadcast_channel_id):
        threading.Thread.__init__(self)
        self.daemon = True

        self._api_token = api_token
        self._broadcast_channel_id = broadcast_channel_id

        # threaded=False: the threaded poller in this telebot version leaks a
        # thread every time polling fails on a network error, until the
        # process can't start any more threads
        self.bot = telebot.TeleBot(self._api_token, threaded=False)
        self.stop_polling = False

        self.start()

    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=False, interval=0, timeout=20)
            except Exception as err:
                error(err)
            if self.stop_polling:
                break
            sleep(1)

    def stop(self):
        self.stop_polling = True
        self.bot.stop_polling()

    def message(self, msg):
        self.bot.send_message(self._broadcast_channel_id, msg)

    def respond(self, original, msg):
        self.bot.send_message(original.chat.id, msg)

    def send_photo(self, filename, caption=None):
        try:
            with open(filename, 'rb') as photo:
                self.bot.send_photo(self._broadcast_channel_id, photo,
                                    caption=caption)
        except Exception as e:
            error("Error sending photo: %s" % str(e))
