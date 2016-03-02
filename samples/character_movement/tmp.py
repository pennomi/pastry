# TODO: Roadmap:
# * Multiplayer via Pastry
# * Enhancement: Queueing of path keyframes
from direct.task.Task import Task
from panda3d.core import Point3, Vec3, NodePath

from direct.actor import Actor
from direct.showbase.ShowBase import ShowBase

from time import time as now
from panda_utils import RayPicker, MouseRayPicker, EdgeScreenTracker


class Keyframe:
    """Track a value relative to some time. When multiple Keyframes are put
    together, you can create a lovely smooth path, even with network latency.
    """
    def __init__(self, value, time=None):
        self.value = value
        if not time:
            time = now()
        self.time = time


class Avatar:
    speed = 3

    def __init__(self, initial_position=Point3.zero()):
        # TODO: Should be a list of keyframes
        self.start_kf = Keyframe(initial_position, time=now())
        self.end_kf = Keyframe(initial_position, time=now())

        # Avatar setup
        self.nodepath = NodePath('avatar')
        self.nodepath.reparentTo(base.render)

        # Prepare animation state
        self._model = Actor.Actor('models/Sinbad', {
            "runTop": "models/Sinbad-RunTop",
            "runBottom": "models/Sinbad-RunBase",
            "dance": "models/Sinbad-Dance.001",
            "idle": "models/Sinbad-IdleTop",
        })
        bottom_parts = [
            "Toe.L", "Toe.R",
            "Foot.L", "Foot.R",
            "Calf.L", "Calf.R",
            "Thigh.L", "Thigh.R",
            "Waist", "Root",
        ]
        # TODO: Finish Upper subparts list
        top_parts = [
            "Torso", "Chest", "Neck", "Head",
            "Clavicle.L", "Clavicle.R",
            "Ulna.L", "Ulna.R",
            "Hand.L", "Hand.R",
        ]
        self._model.makeSubpart("top", top_parts, excludeJoints=bottom_parts)
        self._model.makeSubpart("bottom", bottom_parts, excludeJoints=top_parts)
        self._model.setHprScale(180, 0, 0, .2, .2, .2)
        self._model.reparentTo(self.nodepath)
        self.stand()

        # show where the avatar is headed TODO: Use an arrow or something?
        self._marker = base.loader.loadModel('models/Sinbad')
        self._marker.reparentTo(base.render)
        self._marker.setScale(.05, .05, .05)

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
        self.nodepath.setX(current_pos.x)
        self.nodepath.setY(current_pos.y)

        # Update avatar z pos to snap to floor
        origin = Point3(
            self.nodepath.getX(), self.nodepath.getY(), 5)
        direction = Vec3(0, 0, -1)
        point = FLOOR_PICKER.from_ray(
            origin, direction, condition=lambda o: o.getName() == 'Plane')
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

    def run(self):
        if self._model.getCurrentAnim() not in ["runTop", "runBottom"]:
            self._model.loop("runTop", partName="top")
            self._model.loop("runBottom", partName="bottom")

    def stand(self):
        if not self._model.getCurrentAnim() == 'idle':
            self._model.loop("idle")


class World(ShowBase):
    def __init__(self):
        super().__init__()
        self.avatar = Avatar()

        # The map
        self.terrain = self.loader.loadModel("models/level1")
        self.terrain.reparentTo(self.render)

        EdgeScreenTracker(self.avatar.nodepath, Point3(0, 0, 1))
        self.accept('mouse1', self.on_click)
        self.taskMgr.add(self.game_loop, "game_loop")  # start the gameLoop task

        self.mouse_picker = MouseRayPicker()

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


base = World()
FLOOR_PICKER = RayPicker()
base.run()
