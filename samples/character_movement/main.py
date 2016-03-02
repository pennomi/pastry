# ROADMAP
# * Multiplayer via Pastry
# * Enhancement: Queueing of path keyframes
import asyncio
import sys
from uuid import uuid4

from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task
from panda3d.core import Point3, Vec3, TextNode

from direct.showbase.ShowBase import ShowBase

from time import time as now

from agent import PastryAgent
from client import PastryClient
from distributed_objects import DistributedObjectClassRegistry
from multiserver import MultiServer
from samples.character_movement.panda_utils import RayPicker, MouseRayPicker, \
    EdgeScreenTracker

from samples.character_movement.sinbad import Sinbad
from zone import PastryZone


class Keyframe:
    """Track a value relative to some time. When multiple Keyframes are put
    together, you can create a lovely smooth path, even with network latency.
    """
    def __init__(self, value, time=None):
        self.value = value
        if not time:
            time = now()
        self.time = time


class Avatar(Sinbad):
    speed = 3

    def __init__(self, initial_position=Point3.zero()):
        # TODO: Make into a list of keyframes to do waypoints
        self.start_kf = Keyframe(initial_position, time=now())
        self.end_kf = Keyframe(initial_position, time=now())

        # show where the avatar is headed TODO: Use an arrow or something?
        self._marker = base.loader.loadModel('models/Sinbad')
        self._marker.reparentTo(base.render)
        self._marker.setScale(.05, .05, .05)

        super().__init__()

    def update(self):
        # Calculate the position I should be based off of speed and time
        travel_vector = (self.end_kf.value - self.start_kf.value)
        percent_complete = (
            1 - (self.end_kf.time - now()) /
            (self.end_kf.time - self.start_kf.time)
        )
        if percent_complete > 1:
            # We must be done. Stop animating.
            self.stand()
            return
        current_pos = self.start_kf.value + travel_vector * percent_complete

        # Update avatar z pos to snap to floor
        picker = RayPicker()  # TODO: Reuse instead of instantiating
        point = picker.from_ray(
            Point3(current_pos.x, current_pos.y, 5),
            Vec3(0, 0, -1),
            condition=lambda o: o.getName() == 'Plane')
        self.nodepath.setPos(point)

    def set_destination(self, point):
        # Calculate the keyframes
        ds = point - self.nodepath.get_pos()
        arrival_seconds = ds.length() / self.speed
        self.start_kf = Keyframe(self.nodepath.get_pos())
        self.end_kf = Keyframe(point, now() + arrival_seconds)

        # Now visually make the character move
        self.nodepath.lookAt(point)
        self.nodepath.setP(0)
        self.run()

        # Show a marker
        self._marker.setPos(point)


class World(ShowBase):
    def __init__(self):
        super().__init__()

        # Put some directions on screen.
        self.title = OnscreenText(
            text="Pastry Tutorial - Character Movement",
            style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            pos=(0.7, -0.95), scale=.07)
        self.escape_text = OnscreenText(
            text="ESC: Quit", parent=self.a2dTopLeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1),
            align=TextNode.ALeft, scale=.05)
        self.mouse_text = OnscreenText(
            text="Left-click and drag: Pick up and drag piece",
            parent=self.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.16), scale=.05)

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
    Avatar
)


class ChessClient(PastryClient):
    registry = REGISTRY
    account_id = str(uuid4())
    game = None

    def setup(self):
        self.subscribe("grassy-field")
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
    zone_id = "grassy-field"

    log_color = "\033[92m"
    log_name = "Zone"

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
        pass

    def client_connected(self, client_id):
        print("connected", client_id)

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
        to_start = ChessClient()
    else:
        raise ValueError("Must specify server or client in the command.")
    to_start.run()
