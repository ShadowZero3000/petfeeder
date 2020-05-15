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
- Checkout this repo on the Pi in /opt/petfeeder (Or elsewhere, but up to you to fix paths)
- Run bash /opt/petfeeder/install/install.sh, or do what it does yourself
- Reboot the pi and cross your fingers (Or `systemctl daemon-reload` and `systemctl start petfeeder`)
- Load up the pi's IP in a browser, and configure the Telegram integration, Healthchecks, and meals as you desire


## TODO

There's a todo file, but also I need to write more documentation, specifically how to wire up the circuitry.

## Important security notice

At the moment this does ZERO to verify that users in Telegram are authorized to do things, so if anyone chats up your bot, they could....feed your pets, I guess. (Or delete your schedules, or get your healthcheck unique url). All of this seems sufficiently low risk that I'll come back and fix it later (Adding a simple "What's the password" type thing).

However, and more importantly: This starts up a webserver on the Raspberry Pi on port 80 (Not SSL because I'm lazy) which grants full access to manage/read schedules and activate the feeder. DO NOT PUT THIS ON THE FUCKING INTERNET.

I take zero responsibility for any "bad things" that may occur due to this.

Also, it doesn't currently do a great job of validating inputs, so if you request negative feedings, it won't start pumping your cat's stomach...it'll probably crash, or do nothing. :shrug:
