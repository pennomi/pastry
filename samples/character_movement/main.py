# coding=utf-8
"""
This sample shows how to use keyframe-based movement for characters within a
scene.
 * Enhancement: Queueing of path keyframes
"""
import asyncio
import sys
from uuid import uuid4

from agent import PastryAgent
from client import PastryClient
from distributed_objects import DistributedObjectClassRegistry
from multiserver import MultiServer
from samples.character_movement.avatar import Avatar
from samples.character_movement.game import Game
from samples.character_movement.objects import Character
from zone import PastryZone


# Register all DOs here; this variable propagates to all the various components
REGISTRY = DistributedObjectClassRegistry(
    Character
)


class MovementClient(PastryClient):
    """Allow connections to the game."""
    registry = REGISTRY
    game = None

    def setup(self):
        self.subscribe("overworld")
        asyncio.ensure_future(self.run_panda())
        self.game = Game()

    def object_created(self, obj):
        # TODO: This is a kinda sucky pattern
        if isinstance(obj, Character):
            new_avatar = Avatar(obj, self)
            self.game.avatars.append(new_avatar)
            if self.id == obj.owner:
                self.game.bind_camera(new_avatar)
        else:
            print("Unhandled object", obj)

    def object_updated(self, obj):
        print("updated", obj)
        obj.avatar.move()

    def object_deleted(self, obj):
        print('deleted:', obj)
        for a in self.game.avatars:
            if a.do == obj:
                self.game.avatars.remove(a)
                a._marker.removeNode()
                a._model.removeNode()

    async def run_panda(self):
        while True:
            self.game.taskMgr.step()
            await asyncio.sleep(1 / 60)  # 60 FPS


class MovementAgent(PastryAgent):
    """The most basic agent that's possible."""
    registry = REGISTRY

    log_color = "\033[93m"
    log_name = "Agent"

    async def validate_credentials(self, credentials: dict) -> str:
        """Skip authentication and just return a random client ID."""
        return uuid4()


class MovementZone(PastryZone):
    """Keep track of connected people and sync their movement state."""
    registry = REGISTRY
    zone_id = "overworld"

    log_color = "\033[92m"
    log_name = "Overworld Zone"
    characters = []

    def setup(self):
        self.characters = []

    def client_connected(self, client_id: str) -> None:
        self.log("connected", client_id)
        new_player = Character(zone=self.zone_id, owner=client_id)
        self.characters.append(new_player)
        self.save(new_player)

    def client_disconnected(self, client_id: str) -> None:
        """Remove the character belonging to the client because they left."""
        # TODO: Is this even a thing?
        for c in self.characters:
            if c.owner == client_id:
                c._delete()
                self.save(c)

    def object_created(self, obj):
        self.log("created:", len(self.objects))

    def object_updated(self, obj):
        self.log("updated:", obj)

    def object_deleted(self, obj):
        self.log("deleted:", len(self.objects))


if __name__ == "__main__":
    if 'server' in sys.argv:
        to_start = MultiServer(MovementAgent, MovementZone)
    elif 'client' in sys.argv:
        to_start = MovementClient()
    else:
        raise ValueError("Must specify server or client in the command.")
    to_start.run()
