# ROADMAP
# * Multiplayer via Pastry
# * Enhancement: Queueing of path keyframes
import asyncio
import sys
from uuid import uuid4

from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task
from panda3d.core import Point3, TextNode

from direct.showbase.ShowBase import ShowBase


from agent import PastryAgent
from client import PastryClient
from distributed_objects import DistributedObjectClassRegistry
from multiserver import MultiServer
from samples.character_movement.avatar import Avatar
from samples.character_movement.panda_utils import MouseRayPicker, \
    EdgeScreenTracker

from samples.character_movement.objects import Character
from zone import PastryZone


INSTRUCTION_TEXT = """ESC: Quit
Left-click: Move to position
Screen edges: Rotate camera
"""


class World(ShowBase):
    def __init__(self):
        super().__init__()

        # Put some directions on screen.
        self.title = OnscreenText(
            text="Pastry Tutorial - Character Movement",
            style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            pos=(0.7, -0.95), scale=.07)
        self.escape_text = OnscreenText(
            text=INSTRUCTION_TEXT,
            parent=self.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1), scale=.05)

        # Escape quits
        self.accept('escape', sys.exit)

        # Initialize game objects
        self.avatar = Avatar()
        self.terrain = self.loader.loadModel("models/level1")
        self.terrain.reparentTo(self.render)

        # Set up the mouse picker
        self.mouse_picker = MouseRayPicker()
        self.accept('mouse1', self.on_click)

        # Add the camera controller
        EdgeScreenTracker(self.avatar.nodepath, Point3(0, 0, 1))

        # start the game loop  TODO asyncio
        self.taskMgr.add(self.game_loop, "game_loop")

    def on_click(self):
        """Handle the click event."""
        point = self.mouse_picker.from_mouse(
            # Only include the ground
            condition=lambda o: o.getName() == 'Plane')
        if not point:
            return
        self.avatar.set_destination(point)

    def game_loop(self, task):
        # Move the avatar
        self.avatar.update()

        return Task.cont


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
        self.game = World()

    async def run_panda(self):
        while True:
            self.game.taskMgr.step()
            await asyncio.sleep(1 / 60)  # 60 FPS

    def object_created(self, obj):
        print("created", obj)

    def object_updated(self, obj):
        print("updated", obj)

    def object_deleted(self, obj):
        print('deleted:', obj)


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
    log_name = "Zone"
    avatars = []

    def setup(self):
        # White's perspective
        # piece_order = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)
        # # Convenient kwargs
        # white = {"color": "white", "zone": self.zone_id}
        # black = {"color": "black", "zone": self.zone_id}
        # pieces = (
        #     [Pawn(square=i, **white) for i in range(8, 16)] +
        #     [Pawn(square=i, **black) for i in range(48, 56)] +
        #     [piece_order[i](square=i, **white) for i in range(8)] +
        #     [piece_order[i](square=i + 56, **black) for i in range(8)]
        # )
        # self.save(*pieces)
        self.avatars = []

    def client_connected(self, client_id):
        print("connected", client_id)
        self.avatars.append()

    def object_created(self, obj):
        print("objects:", len(self.objects))

    def object_updated(self, obj):
        print("objects:", len(self.objects))

    def object_deleted(self, obj):
        print("objects:", len(self.objects))


if __name__ == "__main__":
    if 'server' in sys.argv:
        to_start = MultiServer(MovementAgent, MovementZone)
    elif 'client' in sys.argv:
        to_start = MovementClient()
    else:
        raise ValueError("Must specify server or client in the command.")
    to_start.run()
