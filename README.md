Pastry is a DistributedObject architecture that makes creating MMO games easy as pie!

Here's some architecture inspiration material:
http://www.youtube.com/watch?v=JsgCFVpXQtQ
http://www.youtube.com/watch?v=r_ZP9SInPcs
http://www.youtube.com/watch?v=SzybRdxjYoA
http://twvideo01.ubm-us.net/o1/vault/gdconline10/slides/11516-MMO_101_Building_Disneys_Sever.pdf
http://dl.acm.org/citation.cfm?id=950566.950589

DistributedObject class:

 * Functions like a Django Model, with metaclass MAGIC
 * Behaves differently depending on if you're an AI, Client, or OTP Server
 * Standard Notifications
    * Created
    * Updated
    * Deleted
    * Other (Kind of like RPC?) (a @distributed decorator on func?)
 * Must have an owner, which defaults to the AI
 * Has a UUID (DoID)
 * Fields:
    * int
    * float
    * str
    * bytes (print in hex)
    * datetime
    * array
 * Field keywords:
    * required
    * ram (force to sync to new connections)
    * db (permanently persist)
    * broadcast (public)
    * clsend (a client has permission to set this)
    * ownsend (only the owner may set this)
    * ai (only the AI may set this)
 * Fields can have:
    * Validators
    * Clean methods

OTP Server:

 * Relays message back and forth. Handles "interest"
 * Components:
    * Msg Director (sends messages)
    * State Server (persists objects in memory)
    * DB (non-volatile persistence)
    * Client Agent (?)
 * State Server:
    * Holds a zone graph
    * Each zone has DOs in it
    * For instance, a GRID of zones, where client has interest in adj. zones
    * For instance, a tavern
    * Interest (and zones) are nested. But is this necessary for me?
    * Adding interest sends client "create" on all DOs
    * Upon full sync, send "interest complete". But this is generally not good.
    * Removing interest sends client "delete" on all DOs
 * UberDOG:
    * Game-globals
    * Stateless
    * Things like auth

AI:

 * Privileged Client. Probably subclasses that?
 * Basically IS the game logic
 * One AI per zone. Or could there be more? Need at least one.

Client:

 * Normal connection from a user.
 * Must have clock synchronization with server
 * Subscribes to "interests" which are basically zones
 * Unsubscribes when moving away from that zone
 * Disable vs Delete so as to not crash