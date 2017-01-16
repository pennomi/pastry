from distributed_objects import DistributedObject, Field


class Character(DistributedObject):
    """Abstract class for characters."""
    # model_path = Field(str)
    destination = Field(tuple)
    # color = Field(str)
    # name = Field(str)
    # location_keyframes = Field(list)
