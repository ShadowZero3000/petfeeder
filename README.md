# petfeeder
A Raspberry Pi managed pet feeder with chat and web interfaces

## Purpose

I have one of these petfeeders: https://www.amazon.com/gp/product/B07K9PBMRB
It's logic board is terrible. It resets the scheduling on power loss, and I would have no idea if it fed the cats.
Thus, I've elected to replace that logic board with one that I can manage from a web interface or Telegram, and get notifications when it works.

This is very much a work in progress. I'd like to have alerting/messaging when we don't see food actually dispensed (in case it's empty, or failed) etc... but we'll get there over time.

## Requirements

A petfeeder with circuitry you can mess with (Basically a motor you can put a relay on to control and a reed switch to identify when servings are completed to turn off the motor).

A Raspberry Pi (I'm flipping between a Pi3b and a Pi Zero W) configured to talk on your network.

A Telegram API key (optional) and channel for broadcasting messages (also optional).

A Healthchecks.io account (optional) for alerts when it goes down.

## Instructions

- Set up your Pi as per usual
- Checkout this repo on the Pi in /opt (Or elsewhere, but up to you to fix paths)
- Install Python 3
- Pip install virtualenv
- Enter the virtualenv and pip install -r requirements.txt
- Run bash /opt/install/install.sh, or do what it does yourself (Currently very little)
- Edit /opt/envfile, put in:

    ```
    TELEGRAM_API_TOKEN=_fill this in_
    TELEGRAM_BROADCAST_ID=_fill this in_
    ```
- Reboot the pi and cross your fingers (Or `systemctl daemon-reload` and `systemctl start petfeeder`)


## TODO

There's a todo file, but also I need to write more documentation, specifically how to wire up the circuitry.
