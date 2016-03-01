from distributed_objects import DistributedObject, Field


class Piece(DistributedObject):
    """An abstract class for pieces"""
    square = Field(int)  # 0-63 represents all positions
    color = Field(str)


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
