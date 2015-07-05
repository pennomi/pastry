import asyncio
import sys
from uuid import uuid4
from agent import PastryAgent
from client import PastryClient
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

    models = {}

    def setup(self):
        self.subscribe("chess-room-01")
        asyncio.async(self.run_panda())
        self.game = ChessboardDemo(self)

    @asyncio.coroutine
    def run_panda(self):
        taskMgr.step()
        yield from asyncio.sleep(1 / 60)  # 60 FPS
        asyncio.async(self.run_panda())

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
        #self.game.pieces[obj.square] = model, obj

    def object_updated(self, obj):
        model = self.models[obj.id]
        model.setPos(square_pos(obj.square))
        # self.game.pieces[obj.square] = model, obj

    def object_deleted(self, distributed_object):
        print('objects:', len(self.objects))


class ChessAgent(PastryAgent):
    registry = CHESS_REGISTRY

    def authenticate(self, *args, **kwargs):
        # Right now, this is public
        return True


class ChessZone(PastryZone):
    registry = CHESS_REGISTRY
    zone_id = "chess-room-01"

    def setup(self):
        # The order of pieces on a chessboard from white's perspective. This
        # list contains the constructor functions for the piece classes defined
        # below
        piece_order = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)

        for i in range(8, 16):
            # Load the white pawns
            p = Pawn(zone=self.zone_id, square=i, color="white")
            self.objects.create(p)
        for i in range(48, 56):
            # load the black pawns
            p = Pawn(zone=self.zone_id, square=i, color="black")
            self.objects.create(p)
        for i in range(8):
            # Load the special pieces for the front row and color them white
            p = piece_order[i](zone=self.zone_id, square=i, color="white")
            self.objects.create(p)
            # Load the special pieces for the back row and color them black
            p = piece_order[i](zone=self.zone_id, square=i+56, color="black")
            self.objects.create(p)

    def object_created(self, obj):
        print("objects:", len(self.objects))

    def object_updated(self, obj):
        print("objects:", len(self.objects))

    def object_deleted(self, obj):
        print("objects:", len(self.objects))


if __name__ == "__main__":
    thing = sys.argv[1]  # eg. python main.py FOO
    if thing == 'agent':
        to_start = ChessAgent()
    elif thing == 'client':
        to_start = ChessClient()
    elif thing == 'zone':
        to_start = ChessZone()
    else:
        raise ValueError('Must be agent, client or zone')
    to_start.run()
