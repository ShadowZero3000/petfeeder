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

        self.bot = telebot.TeleBot(self._api_token)

        self.start()

    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=False, interval=0, timeout=20)
            except Exception as err:
                error(err)
            sleep(1)

    def message(self, msg):
        self.bot.send_message(self._broadcast_channel_id, msg)

    def respond(self, original, msg):
        self.bot.send_message(original.chat.id, msg)
