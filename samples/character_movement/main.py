import asyncio
from uuid import uuid4
from agent import PastryAgent
from client import PastryClient
from multiserver import MultiServer
from distributed_objects import DistributedObjectClassRegistry
from zone import PastryZone
from samples.chessboard.objects import Pawn, Knight, Bishop, Rook, Queen, King
import builtins
import sys
from direct.showbase.ShowBase import ShowBase
#from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import TextNode
from panda3d.core import LPoint3, LVector3, BitMask32
from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task

# I put these in so my linter doesn't explode.
try:
    base = builtins.base
    render = builtins.render
    camera = builtins.camera
    loader = builtins.loader
    taskMgr = builtins.taskMgr
except AttributeError:
    pass


class MovementDemo(ShowBase):
    def __init__(self, client):
        ShowBase.__init__(self)
        self.client = client

        self.title = OnscreenText(
            text="Pastry Tutorial - Prototype MMO Character Movement",
            style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            pos=(0.8, -0.95), scale = .07)
        self.escape_text = OnscreenText(
            text="ESC: Quit", parent=base.a2dTopLeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1),
            align=TextNode.ALeft, scale = .05)
        self.mouse_text = OnscreenText(
            text="Left-click and drag: Pick up and drag piece",
            parent=base.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.16), scale=.05)

        self.accept('escape', sys.exit)  # Escape quits
        self.disableMouse()  # Disable mouse camera control
        camera.setPosHpr(0, -12, 8, 0, -35, 0)  # Set the camera
        self.make_lights()  # Setup default lighting

        # Start the task that handles the picking
        self.mouse_task = taskMgr.add(self.mouse_task, 'mouse_task')
        self.accept("mouse1", self.grab_piece)
        self.accept("mouse1-up", self.release_piece)

    def mouse_task(self, task):
        return Task.cont

    def make_lights(self):  # This function sets up some default lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.8, .8, .8, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(LVector3(0, 45, -45))
        directionalLight.setColor((0.2, 0.2, 0.2, 1))
        render.setLight(render.attachNewNode(directionalLight))
        render.setLight(render.attachNewNode(ambientLight))


# Register all DOs here; this variable propagates to all the various components
CHESS_REGISTRY = DistributedObjectClassRegistry(
    Pawn, Knight, Bishop, Rook, Queen, King
)


class ChessClient(PastryClient):
    registry = CHESS_REGISTRY
    account_id = str(uuid4())

    models = {}

    def setup(self):
        self.subscribe("chess-room-01")
        asyncio.ensure_future(self.run_panda())
        self.game = ChessboardDemo(self)

    async def run_panda(self):
        taskMgr.step()
        await asyncio.sleep(1 / 60)  # 60 FPS
        asyncio.ensure_future(self.run_panda())

    def object_created(self, obj):
        if obj.color == "white":
            color = WHITE
        elif obj.color == "black":
            color = PIECE_BLACK
        else:
            raise ValueError("Invalid color")

        model = loader.loadModel(obj.model_path)
        self.models[obj.id] = model
        model.reparentTo(render)
        model.setColor(color)
        model.setPos(square_pos(obj.square))

    def object_updated(self, obj):
        model = self.models[obj.id]
        model.setPos(square_pos(obj.square))
        # self.game.pieces[obj.square] = model, obj

    def object_deleted(self, distributed_object):
        print('objects:', len(self.objects))


class ChessAgent(PastryAgent):
    registry = CHESS_REGISTRY

    log_color = "\033[93m"
    log_name = "Agent"

    def authenticate(self, *args, **kwargs):
        # Right now, this is public
        return True


class ChessZone(PastryZone):
    registry = CHESS_REGISTRY
    zone_id = "chess-room-01"

    log_color = "\033[92m"
    log_name = "Zone"

    def setup(self):
        # White's perspective
        piece_order = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)
        # Convenient kwargs
        white = {"color": "white", "zone": self.zone_id}
        black = {"color": "black", "zone": self.zone_id}
        pieces = (
            [Pawn(square=i, **white) for i in range(8, 16)] +
            [Pawn(square=i, **black) for i in range(48, 56)] +
            [piece_order[i](square=i, **white) for i in range(8)] +
            [piece_order[i](square=i+56, **black) for i in range(8)]
        )
        self.save(*pieces)

    def object_created(self, obj):
        print("objects:", len(self.objects))

    def object_updated(self, obj):
        print("objects:", len(self.objects))

    def object_deleted(self, obj):
        print("objects:", len(self.objects))


if __name__ == "__main__":
    thing = sys.argv[1]  # eg. python main.py FOO
    if thing == 'server':
        to_start = MultiServer(ChessAgent, ChessZone)
    elif thing == 'client':
        to_start = ChessClient()
    elif thing == 'zone':
        to_start = ChessZone()
    to_start.run()
