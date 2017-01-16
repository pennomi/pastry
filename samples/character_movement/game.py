import sys

from direct.gui.OnscreenText import OnscreenText
from direct.task.Task import Task
from panda3d.core import Point3, TextNode

from direct.showbase.ShowBase import ShowBase
from samples.character_movement.panda_utils import MouseRayPicker, \
    EdgeScreenTracker


INSTRUCTION_TEXT = """ESC: Quit
Left-click: Move to position
Screen edges: Rotate camera
"""


class Game(ShowBase):
    my_avatar = None

    def __init__(self):
        super().__init__()

        # Put some directions on screen.
        self.title = OnscreenText(
            text="Pastry Tutorial - Character Movement",
            style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            pos=(0.7, -0.95), scale=.07)
        self.instruction_text = OnscreenText(
            text=INSTRUCTION_TEXT,
            parent=self.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1), scale=.05)

        # Escape quits
        self.accept('escape', sys.exit)

        # Initialize game objects
        self.avatars = []
        self.terrain = self.loader.loadModel("models/level1")
        self.terrain.reparentTo(self.render)

        # Set up the mouse picker
        self.mouse_picker = MouseRayPicker()
        self.accept('mouse1', self.on_click)

        # start the game loop  TODO asyncio
        self.taskMgr.add(self.game_loop, "game_loop")

    def bind_camera(self, avatar):
        self.my_avatar = avatar
        EdgeScreenTracker(avatar.nodepath, Point3(0, 0, 1))

    def on_click(self):
        """Handle the click event."""
        point = self.mouse_picker.from_mouse(
            # Only include the ground
            condition=lambda o: o.getName() == 'Plane')
        if not point:
            return

        if self.my_avatar:
            self.my_avatar.set_destination(point)

    def game_loop(self, task):
        for a in self.avatars:
            a.update()
        return Task.cont
