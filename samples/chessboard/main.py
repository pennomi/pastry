import asyncio
import sys
from uuid import uuid4
from agent import PastryAgent
from client import PastryClient
from multiserver import MultiServer
from distributed_objects import DistributedObjectClassRegistry
from zone import PastryZone
from samples.chessboard.game import ChessboardDemo, square_pos, PIECE_BLACK, \
    WHITE
from samples.chessboard.objects import Pawn, Knight, Bishop, Rook, Queen, King


# Register all DOs here; this variable propagates to all the various components
CHESS_REGISTRY = DistributedObjectClassRegistry(
    Pawn, Knight, Bishop, Rook, Queen, King
)


class ChessClient(PastryClient):
    registry = CHESS_REGISTRY
    account_id = str(uuid4())
    game = None

    models = {}

    def setup(self):
        self.subscribe("chess-room-01")
        asyncio.ensure_future(self.run_panda())
        self.game = ChessboardDemo(self)

    async def run_panda(self):
        while True:
            taskMgr.step()
            await asyncio.sleep(1 / 60)  # 60 FPS

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

    def _authenticate(self, *args, **kwargs):
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
    else:
        raise KeyError('argument must be (server|client)')
    to_start.run()
