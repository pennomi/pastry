from distributed_objects import DistributedObject, Field


class Character(DistributedObject):
    """Abstract class for characters."""
    model_path = Field(str)
    location_x = Field(int)
    location_y = Field(int)
    color = Field(str)
    name = Field(str)
    animation = Field(str)
    location_keyframes = Field(list)
