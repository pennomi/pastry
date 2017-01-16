# ROADMAP
# * Multiplayer via Pastry
# * Enhancement: Queueing of path keyframes
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
    registry = REGISTRY
    account_id = str(uuid4())
    game = None

    def setup(self):
        self.subscribe("overworld")
        asyncio.ensure_future(self.run_panda())
        self.game = Game()

    def object_created(self, obj):
        print("created", obj)
        new_avatar = Avatar(obj, self)
        self.game.avatars.append(new_avatar)
        if len(self.game.avatars) == 1:
            self.game.bind_camera()

    def object_updated(self, obj):
        print("updated", obj)
        obj.avatar.move()

    def object_deleted(self, obj):
        print('deleted:', obj)

    async def run_panda(self):
        while True:
            self.game.taskMgr.step()
            await asyncio.sleep(1 / 60)  # 60 FPS


class MovementAgent(PastryAgent):
    registry = REGISTRY

    log_color = "\033[93m"
    log_name = "Agent"

    def authenticate(self, *args, **kwargs):
        # Right now, this is public
        return True


class MovementZone(PastryZone):
    registry = REGISTRY
    zone_id = "overworld"

    log_color = "\033[92m"
    log_name = "Overworld Zone"
    avatars = []

    def setup(self):
        self.avatars = []

    def client_connected(self, client_id: str):
        self.log("connected", client_id)
        new_player = Character(zone=self.zone_id)
        self.avatars.append(new_player)
        self.save(new_player)

    def client_disconnected(self, client_id: str):
        # TODO: Is this even a thing?
        pass

    def object_created(self, obj):
        self.log("objects:", len(self.objects))

    def object_updated(self, obj):
        self.log("updated:", obj)

    def object_deleted(self, obj):
        self.log("objects:", len(self.objects))


if __name__ == "__main__":
    if 'server' in sys.argv:
        to_start = MultiServer(MovementAgent, MovementZone)
    elif 'client' in sys.argv:
        to_start = MovementClient()
    else:
        raise ValueError("Must specify server or client in the command.")
    to_start.run()
