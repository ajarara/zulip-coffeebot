
# Zulip-coffeebot
Currently this bot runs on a cold VM. If you'd like to install this on your zulip instance, probably follow https://zulip.readthedocs.io/en/latest/bots-guide.html

# Spec
This section documents how the Coffeebot behaves. Why a spec? See [Joel Spolsky's four part series](https://www.joelonsoftware.com/2000/10/02/painless-functional-specifications-part-1-why-bother/).

## Overview

This bot unites people within a zulip organization in physical proximity with beloved coffee in an efficient, low maintenance way. Coffeebot organizes collectives, providing an interface for those who want coffee and delegates a coffee maker for the collective randomly. 

Users can interact with coffeebot in the following ways.
- `@Coffeebot init` - Initialize a collective
- `@Coffeebot yes` - Join a forming collective
- `@Coffeebot no` - Withdraw from a forming collective
- `@Coffeebot ping` - Ping all those in the collective. Only the maker may do this.

A collective is a group of people who want coffee. Once a collective is formed, Coffeebot will designate a maker. That maker makes the coffee for the collective. Then once the coffee is made, the maker simply types `@Coffeebot ping` to alert others their coffee is ready. Everyone rejoices.

Please see the [functional details section](#functional-details) for more.

## Functional details

Coffeebot listens in on a set of channels. When mentioned with the phrase `@coffeebot init` in one of the channels, Coffeebot will first check to see if a collective is ongoing. As of now, Coffeebot will only support one collective at a time. If there is one, then Coffeebot will reply to the attempted request to init a collective with a failure message. If there isn't, a collective will be spawned, with the person who initialized as the collective leader. There is no special behavior for the leader currently. 

People are then free to request coffee with `@coffeebot yes`, undoing with `@coffeebot no`. Coffeebot will continue to take requests until one of these conditions are satisfied:
- 15 minutes have passed since the collective has been initialized
- 4 people have requested coffee in the collective.

Once either of these conditions occur a few things will happen:
- All requests to be a part of the collective will fail, with Coffeebot notifying users, advising them to create a new collective (after a certain amount of time so that the current collective can make their coffee in peace).
- Once this occurs all requests to leave the collective will fail, with Coffeebot notifying the user of the failure. If the user is not the maker, they are free to forfeit their coffee.
- One member of the collective will be randomly chosen to make coffee. Coffeebot will notify all users of the collective who this member is. It is this person's responsibility to make coffee. Coffeebot will not physically enforce coffee creation for all foreseeable versions. This may change.


After the coffee is made, the maker may ping all those who are in the collective they are in with `@coffeebot ping`, within 2 hours. Only the maker can perform this ping (there is nothing stopping anyone anywhere from pinging manually). This is to make the responsibility concrete. In the case that the maker has been the maker of a previous collective that occurred within the last two hours, Coffeebot will ping all those that are in the most recent.

At any point in this event loop, anyone in a collective or otherwise may message `@Coffeebot love` or `I love you @Coffeebot` for a random reciprocating emoji. Coffeebot appreciates your gratitude.


## Technical details

The below is a working draft. I wouldn't bother reading it in its current state.

_Note:_ Coffeebot is not currently implemented. Rather than say words like "Coffeebot would do so and so" I'm just going to pretend it's already implemented and describe its behavior in words like "Coffeebot does so and so", and then simply delete this line when that is the case. The idea is to flesh out a complete but minimal technical spec. Afterwards, any desired functionality would use the future tense like normal.


### Collectives
A collective is a group of people tied to a Zulip thread, with a leader. They can be in two states: open or closed. When a collective is open, it can add users to itself, or drop them, on request. It takes in these requests from a queue that coffeebot pushes into, to prevent any weird intermediate state. Collectives are class based, with the following methods:

- constructor

Requires a leader, optionally a max-size and timeout (in minutes).

- close

Closes the collective off to new users. Closing the same collective twice raises ValueError.

- add_user 

Adds user to the collective if it is not closed. Raises KeyError otherwise.

- drop_user

Removes user to the collective if it is not closed. Raises KeyError otherwise.

- read_queue

Interface for coffeebot to place events into. Every action is preceded by reading exactly one element, called a Directive, from the queue. Directives are simply namedtuples, that have command and arguments (possibly none).

- dispatch

Takes a Directive and dispatch on the command attribute. Pass arguments to whatever the command gets mapped to.

- attempt_queue

Check if the collective is closed. If it's not closed, check if it should be.
Check the queue for events. If there is anything in the queue, pop it off, apply dispatch on it.

- should_close

As of now: check if the collective is stale (time remaining on the timeout), check if the collective is full. Return either of these.

- is_stale

Just checks timeout. This method probably errs on too much separation.

- is_full

Checks if the size of the collective exceeds max_size (default 5).

- Completely irrelevant:

- \_\_len__

Returns the number of users in the collective.



### Command - Function mapping
Coffeebot uses Zulip's API to listen in on a list of streams, defined in the Coffeebot constructor. When Coffeebot is mentioned, it'll attempt to parse for these keywords in the message that mentioned it:

