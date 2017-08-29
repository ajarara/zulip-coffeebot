# Another attempt
Instead of defining collectives and having their design meet the interface design with the coffeebot as an intermediary, instead I'll define the interface and enumerate all the exceptional events and handle those from coffeebot's perspective.

## Philosophy
Coffeebot should be as quiet as possible, using emoji to signify confirmation and state to the user, only responding during exceptional events. If coffeebot was PM'd, Coffeebot will only update the collective count, not by sending a new message, but by decrementing the count using the :three, two, one: emotes. The only problem is that users might click on these emotes and make keeping track confusing... that's a significant problem I think. Maybe instead only post when the collective is about to be closed.. maybe silent collectives are more trouble then they are worth. Perhaps try to accomodate for it, but that's difficult without writing about it.

All commands could also specify keywords, like collective or timeout. The interface could be:
:collective 12
or
collective=12

I like keyword style tokens because there's no ambiguity between if whitespace is allowed. A possible problem is:

- "@coffeebot join:collective 15"

but this doesn't have to fail. Colons are not otherwise present. Specifically ignore colons that have whitespace after them, though, as that is normal English (see: this document)


## Initializing a collective
Commands:
- "@coffeebot init\w*"
- "@coffeebot start"

Possibly supported down the line:
Custom timeout, custom collective size

Possible responses:
- User is already in an open collective

Refer the user to their collective.

- *

Create a new collective. Append it to the queue.

## Joining a collective by topic
Commands:
- "@coffeebot yes"
- "@coffeebot join"
- "@coffeebot in"

Possibly supported down the line:
- Emoting with :coffee: on the @coffeebot init reply

Possible responses:
- User is already in an open collective

Refer the user to their collective. This requires a map from user to collectives.

I also need a map from collective ids to users. I can store them in the same map. Just.. weird.

If I want to iterate over them, I could do two things:
filter the iterator for only collectives

or create a separate map for users -> collectives and collectives -> users.

- No open collectives in topic

Tell the user there are no active collectives in the topic. To join a collective without posting in a specific topic, show the user how to join a collective by name.

- *
Put the user in the most recent open collective in the stream.


## Leaving a collective by topic
Commands:
- "@coffeebot no"
- "@coffeebot leave"
- "@coffeebot out"

Possibly supported down the line:
- Removing the :coffee: emote on the @coffeebot init reply

This specific action has a special case, removing the :coffee: emote after the collective is closed should have coffeebot do what exactly? Message the user privately and tell them "too bad you're in." Maybe let the user know that they can forfeit their coffee instead, but they can't forfeit being the maker.

Possible responses:
- Last collective in topic has been closed in the last two hours.

If the user isn't the maker:
Drop them from the collective, ping the maker to let them know to make n-1 coffees.

If the user is:
Reject their request. 

- User is in the open collective.
Drop them from the collective. Acknowledge their confirmation. 

- User is not in the open collective.
Warn them they're not in the collective.


## Joining a collective by ID
Commands: same as joining by topic with a :collective # arg.

- The collective is closed.

