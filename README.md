
# Zulip-coffeebot
Currently this bot runs on a cold VM. If you'd like to install this on your zulip instance, probably follow https://zulip.readthedocs.io/en/latest/bots-guide.html



# Spec
This section documents how the Coffeebot behaves. 

## Overview

This bot unites people within a zulip organization in physical proximity with beloved coffee in an efficient, low maintenance way. Coffeebot organizes collectives, providing an interface for those who want coffee and delegates a coffee maker for the collective randomly. 

## Functional details

Coffeebot listens in on a set of channels. When mentioned with the phrase `@coffeebot init` in one of the channels, Coffeebot will first check to see if a collective is ongoing. As of now, Coffeebot will only support one collective at a time. If there is one, then Coffeebot will reply to the attempted request to init a collective with a failure message. If there isn't, a collective will be spawned, with the person who initialized as the collective leader. There is no special behavior for the leader currently. 

People are then free to request coffee with `@coffeebot yes`, undoing with `@coffeebot no`. Coffeebot will continue to take requests until one of these conditions are satisfied:
- 15 minutes have passed since the collective has been initialized
- 4 people have requested coffee in the collective.

Once either of these conditions occur a few things will happen:
- All requests to be a part of the collective will fail, with Coffeebot notifying users, advising them to create a new collective (after a certain amount of time so that the current collective can make their coffee in peace).
- Once this occurs all requests to leave the collective will fail, with Coffeebot notifying the user.
- One member of the collective will be randomly chosen to make coffee. Coffeebot will notify all users of the collective who this member is. It is this person's responsibility to make coffee. Coffeebot will not enforce coffee creation for all foreseeable versions. This may change.


After the coffee is made, the maker may ping all those who are in the collective they are in with `@coffeebot ping`, within 2 hours. Only the maker can perform this ping (there is nothing stopping anyone anywhere from pinging manually). In the case that the maker has been the maker of a previous collective that occurred within the last two hours, Coffeebot will ping all those that are in the most recent.

At any point in this event loop, anyone in a collective or otherwise may message `@Coffeebot love` or `I love you @Coffeebot` for a random reciprocating emoji. Coffeebot appreciates your gratitude.

