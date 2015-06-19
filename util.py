

class Channel:
    def __init__(self, *, target_zone=None, object_class=None, method=None,
                 target_user=None):
        """For example"""
        # TODO: Aren't target zone and user the same thing?
        self.target_zone = target_zone
        self.object_class = object_class
        self.method = method
        self.target_user = target_user

    @staticmethod
    def parse(channel_expression):
        """Parses the channel name into a usable description."""
        components = channel_expression.split('.')
        # TODO: If the first piece is a UUID, it's the target user
        # TODO: The zone name
        # TODO: The object class
        # TODO: The method name

    def __str__(self):
        # TODO: Render this to the dotted notation
        return "{}.{}.{}.{}".format(
            self.target_user, self.target_zone, self.object_class, self.method)