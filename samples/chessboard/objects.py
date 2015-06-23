from distributed_objects import DistributedObject, Field


class Piece(DistributedObject):
    """An abstract class for pieces"""
    model_path = Field(str)
    square = Field(int)  # 0-63 represents all positions
    color = Field(str)

    def __init__(self, *, zone=None, **kwargs):
        super().__init__(zone=zone, **kwargs)
        # self.obj = loader.loadModel(self.model_path)
        # self.obj.reparentTo(render)
        # self.obj.setColor(self._get_color())
        # # noinspection PyTypeChecker
        # self.obj.setPos(square_pos(self.square))

    def _get_color(self):
        if self.color == "white":
            return WHITE
        elif self.color == "black":
            return PIECE_BLACK


class Pawn(Piece):
    model_path = "models/pawn"


class King(Piece):
    model_path = "models/king"


class Queen(Piece):
    model_path = "models/queen"


class Bishop(Piece):
    model_path = "models/bishop"


class Knight(Piece):
    model_path = "models/knight"


class Rook(Piece):
    model_path = "models/rook"