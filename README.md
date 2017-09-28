# What is Coffeebot?

Coffeebot is a zulip bot that invites people for coffee. When enough people want coffee, Coffeebot randomly delegates someone from the group of people to make it happen. 

- "@**Coffeebot** init"

Initialize a collective (a group of people who want coffee), with you as the leader. The leader currently has no fancy functionality beyond Coffeebot's utmost respect.

- "@**Coffeebot** yes"

Join an open collective. By joining you affirm you want coffee, and are willing to make coffee for up to 2 others.

- "@**Coffeebot** no"

Drop your commitment to the collective :disappointed_relieved:. You renounce your claim to coffee, and thus don't have to risk making it. Once a collective is closed, you cannot leave it.

- "@**Coffeebot** close"

Close the collective. Only those within it may close it.

- "@**Coffeebot** ping"

Ping all those in the collective (this should only be used to signify coffee is ready, as that's what Coffeebot indicates). Only the maker may do this, but there's nothing stopping someone from pinging everyone manually.

- "@**Coffeebot** state"

Publicly say the state of the collective. This includes the members inside, the time the collective was created, and the approximate time left until the collective timeouts.


# Zulip-coffeebot

```
usage: coffeebot [-h] [--api_key [s0meAP1key]]
                 [--email [coffeebot-bot@$REALM]]
                 [--site [recurse.zulipchat.com]]
                 [--config_file [zuliprc.conf]]

Runtime configuration for Coffeebot

optional arguments:
  -h, --help            show this help message and exit
  --api_key [s0meAP1key]
  --email [coffeebot-bot@$REALM]
  --site [recurse.zulipchat.com]
  --config_file [zuliprc.conf]
```

To install on a NixOS instance, add a file called `zuliprc.conf` to the coffeebot directory, containing your API key, bot email, and zulip realm site [as shown here](https://zulipchat.com/api/). Then, from the root of the repo, `make package` and rsync `dist` to wherever you'd like on the remote machine. Add whereever `coffeebot.nix` is to the imports in your configuration.nix, and rebuild, it will handle the rest.

If you don't want to use a file for your auth details, you can also supply your API key, email, and site directly to the coffeebot.nix file in the ExecStart string using the above usage. It's recommended to keep these secrets in a file external to the config, in a .gitignore'd file, particularly if you're pushing your changes publicly.

This package is not available on Pypi.


# Spec
This section documents how the Coffeebot behaves. Why a spec? See [Joel Spolsky's four part series](https://www.joelonsoftware.com/2000/10/02/painless-functional-specifications-part-1-why-bother/).

## Overview

This bot unites people within a zulip organization in physical proximity with beloved coffee in an efficient, low maintenance way. Coffeebot organizes collectives, providing an interface for those who want coffee to interact with collectives and delegates a coffee maker for the collective randomly, once certain conditions have been met.

Users can interact with coffeebot in the following ways.
- `@Coffeebot init` - Initialize a collective
- `@Coffeebot yes` - Join a forming collective
- `@Coffeebot no` - Withdraw from a forming collective
- `@Coffeebot ping` - Ping all those in the collective. Only the maker may do this.

A collective is a group of people who want coffee. Once a collective is formed, Coffeebot will designate a maker. That maker makes the coffee for the collective. Then once the coffee is made, the maker simply types `@Coffeebot ping` to alert others their coffee is ready. Everyone rejoices.

Please see the [functional details section](#functional-details) for more.

## Functional details

Coffeebot registers an event hook on 'heartbeats' and 'messages'. It feeds these events into a generic dispatch function that checks the type of the event and sends it off to handlers. Given an event and a reference to the API client (the attribute inside Coffeebot is literally called `client`), these handlers can do arbitrary things. The decision of passing the event unchanged to handlers provides flexibility in program extension and maintenance.

### Ideal User Story
Users A, B, C want delicious coffee. Coffeebot is listening on the #coffee zulip stream.

User A posts `@**Coffeebot** init` to a thread named "Completely arbitrary"
Coffeebot responds by creating a collective in memory, and sending a confirmation message. The exact message can be found in the init_collective method of the Coffeebot class.

User B also would like coffee, so they join the collective with `@**coffebot** yes`. Coffeebot acknowledges this with a thumbs up.

Similarly, User C sees all this action and joins in, and Coffeebot acknowledges this too with a thumbs up. Since the default collective size is 3, immediately after Coffeebot closes the collective, selects a maker, and announces that maker.

### State transitions
Collectives go from non-existent -> open -> closed. All open collectives are uniquely identified by the stream and thread they were created in.

`@coffeebot state` shows the user the status of the collective it has in memory, it does not read the thread to determine this information. This means that if Coffeebot is restarted, it will lose all context. This is a flaw.

- non-existent

`@coffeebot init` takes a collective from non-existent -> open

All other commands will yield some message directing users to the appropriate action, in this case initialization.

- open

`@coffeebot close` takes a collective from open -> close
`@coffeebot state` shows the 


People are then free to request coffee with `@coffeebot yes`, undoing with `@coffeebot no`. Coffeebot will continue to take requests until one of these conditions are satisfied:
- 15 minutes have passed since the collective has been initialized
- 4 people have requested coffee in the collective.

Once either of these conditions occur a few things will happen:
- All requests to be a part of the collective will fail, with Coffeebot notifying users, advising them to create a new collective (after a certain amount of time so that the current collective can make their coffee in peace).
- Once this occurs all requests to leave the collective will fail, with Coffeebot notifying the user of the failure. If the user is not the maker, they are free to forfeit their coffee.
- One member of the collective will be randomly chosen to make coffee. Coffeebot will notify all users of the collective who this member is. It is this person's responsibility to make coffee. Coffeebot will not physically enforce coffee creation for all foreseeable versions. This may change.


After the coffee is made, the maker may ping all those who are in the collective they are in with `@coffeebot ping`, within 2 hours. Only the maker can perform this ping (there is nothing stopping anyone anywhere from pinging manually). This is to make the responsibility concrete. In the case that the maker has been the maker of a previous collective that occurred within the last two hours, Coffeebot will ping all those that are in the most recent.

At any point in this event loop, anyone in a collective or otherwise may message `@Coffeebot love` for a random reciprocating emoji. Coffeebot appreciates your gratitude.


