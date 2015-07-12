"""
All internal message types:

NAME:           CHANNEL:                        PAYLOAD:
User Join       {ZONE_ID}.join                  {USER_ID}
User Leave?     {ZONE_ID}.leave                 {USER_ID}
Public create   {ZONE_ID}.create.{DO_CLASS}     {SERIALIZED_DO}
Public update   {ZONE_ID}.update                {SERIALIZED_DO}
Public delete   {ZONE_ID}.delete                {SERIALIZED_DO}
Public call     {ZONE_ID}.call.{DO_METHOD}      {SERIALIZED_ARGUMENTS}
Whisper         {USER_ID}.*                     (same as public)
Custom          {WHATEVER}                      {WHATEVER}

Note that Zone IDs are serialized in the DO anyway, so the duplication of the
ZONE_ID in the channel serves entirely as an internal message pruning system.
"""
# TODO: Should we mark the whispers specially, since they are unique?
# TODO: Method should be an Enum
# TODO: There are subscribe/unsubscribe on the client. Change to join/leave?
# TODO: Add a kill internal message that kills the USER_ID in question. Ouch.

class Channel:
    """A classy representation of channels. This makes it easier
    to route messages cleanly.
    """
    def __init__(self, *, target: str=None, method=None, code_name=None):
        """
        :param target: Either the zone or the user ID.
        :param method: Used to determine what is taking place
        :param code_name: Only used in "create" channels (to pick a class
        from the registry) and in "call" channels (to pick the method that
        should be executed)
        """
        self.target = target
        self.method = method
        self.code_name = code_name
        if self.code_name and self.method not in ["create", "call"]:
            raise TypeError("code_name only used on `create` and `call`")

    @staticmethod
    def parse(channel_expression: str):
        """Parses the channel name into a usable description."""
        target, method, *rest = channel_expression.split('.')
        code = None
        if rest:
            code = rest[0]
        return Channel(target=target, method=method, code_name=code)

    def __str__(self):
        pieces = [self.target, self.method]
        if self.code_name:
            pieces.append(self.code_name)
        return ".".join(pieces)