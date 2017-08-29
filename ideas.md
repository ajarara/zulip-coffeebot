This document provides a way for me to extend Coffeebot without actually extending Coffeebot. Instead it shows me all the ways I should design coffeebot to accomodate for all these ideas down the line.

# Statistics on collectives
This is a little silly. But when each collective is spawned and the maker decided, that might be convenient history for people interested in when they have their coffee. Representations could be in lined, but that's a little hard work, unless I generate them through coffeebot and zulip has an image upload API. This would also require a database and file access, which would necessitate a user.

# API keys should not be baked in but supplied at runtime
Prevents any source issues when I push things to Github. Makes it very simple to change without redeploying.


# Multiple collectives

There are a bunch of ways to tackle this problem.

The first is to uniquely identify every collective. This makes supporting statistics above easy. Exposing this collective ID allows users to communicate effectively which collective they want to interact with (say if someone wanted info).

The next is to only support working on the newest collective if you're in it. Joining a new one while you're in an open one will probably remove you from the old one and put you into the new one. The only way I can think of to rejoin the old one is if the two are in multiple threads, or by referencing the leader. Both of these are awkward interfaces.

The third is to use human friendly names. This is an extension of the first idea, it's fun, but it's also more complicated. There's an issue of running out of names. It could be implemented on top of the first later on, but then it's not a solution to this problem just something I'd like to have.

Leaning towards the first idea.

# Who emanates errors?
Coffeebot is the one interfacing with users. Collectives really shouldn't have any notion of Zulip.

Python has a mantra of EAFP: It's Easier to Ask Forgiveness than Permission.

Not sure if I agree with it, but the mantra indicates to simply pass along all directives to a collective and have it throw errors as needed.

An alternative is to have the error handling inside Coffeebot. Not sure that's the best idea, Coffeebot has exceptional cases of its own. 

Leaning towards EAFP, even though it bothers me.

Having collectives do error handling means that there's a layer of separation between the error and the user. But all Coffeebot really can do is unwrap the args to the error and pass that along.

# Who dispatches?

Each directive must be answered. It's pretty clear it's coffeebot's job to deconstruct the command and push it into a directive.

I think this problem is difficult because directives are the natural thing to put into an event queue. Should each collective have its own event queue? Or should coffeebot immediately..

coffeebot needs the queue because collectives emanate errors. The utmost priority is to not miss an event. Probably need to dive into the Zulip API again to see how events are stored. If the client needs to be listening then that is an issue.
