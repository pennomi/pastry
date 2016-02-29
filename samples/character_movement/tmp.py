# TODO: Roadmap:
# * Multiplayer via Pastry
# * Enhancement: Queueing of path keyframes

import builtins
from panda3d.core import CollisionRay, CollisionTraverser, GeomNode, BitMask32,\
    CollisionNode, Point3, Vec3, CompassEffect, CollisionHandlerQueue, Point2, \
    NodePath

import direct.directbase.DirectStart
from direct.task import Task
from direct.actor import Actor
from direct.interval import LerpInterval as LERP
from direct.showbase.DirectObject import DirectObject
from time import time as now


# Make the linter happy
base = builtins.base
render = builtins.render
camera = builtins.camera
loader = builtins.loader
taskMgr = builtins.taskMgr
messenger = builtins.messenger
globalClock = builtins.globalClock


class Picker:
    def __init__(self, debug=False, type: str="camera"):
        # Init components
        self.traverser = CollisionTraverser()
        self.handler = CollisionHandlerQueue()
        self.node = CollisionNode('picker_ray')  # TODO: Name differently?
        if type == "camera":
            self.nodepath = camera.attachNewNode(self.node)
        else:
            self.nodepath = render.attachNewNode(self.node)
        self.ray = CollisionRay()

        # Set up relationships
        self.node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.node.addSolid(self.ray)
        self.traverser.addCollider(self.nodepath, self.handler)

        # Show collisions?
        if debug:
            self.traverser.showCollisions(render)

    def _iterate(self, condition):
        # TODO: Move condition to the constructor
        # Iterate over the collisions and pick one
        self.traverser.traverse(render)

        # Go closest to farthest
        self.handler.sortEntries()

        for i in range(self.handler.getNumEntries()):
            pickedObj = self.handler.getEntry(i).getIntoNodePath()
            # picker = self.handler.getEntry(i).getFromNodePath()

            if not condition or (condition and condition(pickedObj)):
                point = self.handler.getEntry(i).getSurfacePoint(render)
                return point

        # Too bad, didn't find any matches
        return None

    def from_camera(self, condition=None):
        # Get the mouse and generate a ray form the camera to its 2D position
        mouse = base.mouseWatcherNode.getMouse()
        self.ray.setFromLens(base.camNode, mouse.getX(), mouse.getY())
        return self._iterate(condition)

    def from_ray(self, origin, direction, condition=None):
        # Set the ray from a specified point and direction
        self.ray.setOrigin(origin)
        self.ray.setDirection(direction)
        return self._iterate(condition)


def clamp(v, minmax):
    minimum, maximum = minmax
    return max(minimum, min(v, maximum))


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
        self.nodepath = NodePath('avatar prime')
        self.nodepath.reparentTo(render)
        self.nodepath.setCollideMask(BitMask32.allOff())  # no collisions!

        # Prepare animation state
        self.model = Actor.Actor('models/Sinbad', {
            "runTop": "models/Sinbad-RunTop",
            "runBottom": "models/Sinbad-RunBase",
            "dance": "models/Sinbad-Dance.001",
            "idle": "models/Sinbad-IdleTop",
        })
        self.model.setHprScale(180, 0, 0, .2, .2, .2)
        self.model.reparentTo(self.nodepath)
        self.stand()

        # show where the avatar is headed TODO: Use an arrow or something?
        self.marker = loader.loadModel('models/Sinbad')
        self.marker.reparentTo(render)
        self.marker.setScale(.05, .05, .05)
        self.marker.setCollideMask(BitMask32.allOff())

    def update(self, dt):
        # Calculate the position I should be based off of speed and time
        travel_vector = (self.end_kf.value - self.start_kf.value)
        percent_complete = 1 - (self.end_kf.time - now()) / (self.end_kf.time - self.start_kf.time)
        if percent_complete > 1:
            # We must be done. Stop animating.
            self.stand()
            return
        current_pos = self.start_kf.value + travel_vector * percent_complete
        self.nodepath.setX(current_pos.x)
        self.nodepath.setY(current_pos.y)

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

    def run(self):
        # TODO: Make Sinbad do half-body animations
        # actor.makeSubpart("legs", ["Left Thigh", "Right Thigh"])
        # actor.makeSubpart("torso", ["Head"], ["Left Thigh", "Right Thigh"])
        # actor.loop("walk", partName="legs")
        # actor.loop("reload", partName="torso")
        if not self.model.getCurrentAnim() == 'runBottom':
            self.model.loop('runBottom')

    def stand(self):
        if not self.model.getCurrentAnim() == 'idle':
            self.model.loop("idle")


# TODO: add a right-click-drag rotation as well
class EdgeScreenTracker(DirectObject):
    """Mouse camera control interface."""

    def __init__(self, avatar, offset=Point3.zero(), initial_zoom=10,
                 zoom_limits=(2, 20), pitch_limits=(-80, -10)):
        super().__init__()
        base.disableMouse()
        self.zoom = initial_zoom
        self.speed = 1.0 / 20.0
        self.zoom_limits = zoom_limits
        self.pitch_limits = pitch_limits

        # Move the camera with the target
        self.target = avatar.attachNewNode('camera target')
        self.target.setPos(offset)

        # Though the camera parents to the avatar, lock its rotation to render
        self.target.node().setEffect(CompassEffect.make(render))
        camera.reparentTo(self.target)
        camera.setPos(0, -self.zoom, 0)
        self.rotate_camera(Point2(0, 0))
        self.accept('wheel_up', self.adjust_zoom, [0.7])
        self.accept('wheel_down', self.adjust_zoom, [1.3])
        # TODO: Polish up this keyboard movement
        self.accept('arrow_right-repeat', self.rotate_camera, [Point2(10, 0)])
        self.accept('arrow_left-repeat', self.rotate_camera, [Point2(-10, 0)])
        taskMgr.add(self.mousecam_task, "mousecam_task")

    def mousecam_task(self, task):
        # Lock the camera on the target
        self.position_camera()
        camera.lookAt(self.target)

        # Handle border-panning
        if not base.mouseWatcherNode.hasMouse():
            return Task.cont
        mpos = base.mouseWatcherNode.getMouse()
        if mpos.getX() > 0.99:
            self.rotate_camera(Point2(-10, 0))
        elif mpos.getX() < -0.99:
            self.rotate_camera(Point2(10, 0))
        if mpos.getY() > 0.9:
            self.rotate_camera(Point2(0, -3))
        elif mpos.getY() < -0.9:
            self.rotate_camera(Point2(0, 3))
        return Task.cont  # loop again.

    def rotate_camera(self, arc):
        newP = clamp(self.target.getP() - arc.getY(), self.pitch_limits)
        newH = self.target.getH() + arc.getX()  # Not clamped, just added.
        LERP.LerpHprInterval(
            self.target, self.speed, Vec3(newH, newP, self.target.getR())
        ).start()

    def adjust_zoom(self, zoom_factor):
        """Scale and clamp zoom level, then set distance by it."""
        self.zoom = clamp(self.zoom * zoom_factor, self.zoom_limits)

    def position_camera(self):
        """Maintain a constant distance to the target."""
        vec = camera.getPos()
        vec.normalize()
        vec *= self.zoom
        camera.setFluidPos(vec)


class World(DirectObject):
    def __init__(self):
        super().__init__()
        self.avatar = Avatar()

        # The map
        self.terrain = loader.loadModel("models/level1")
        self.terrain.reparentTo(render)

        EdgeScreenTracker(self.avatar.nodepath, Point3(0, 0, 1))
        self.accept('mouse1', self.on_click)
        taskMgr.add(self.game_loop, "game_loop")  # start the gameLoop task

        self.mouse_picker = Picker()
        # TODO: Remove type and make it into a subclass?
        self.floor_picker = Picker(type="floor")

    def on_click(self):
        """Handle the click event."""
        point = self.mouse_picker.from_camera(
            # Only include the ground
            condition=lambda o: o.getName() == 'Plane')
        if not point:
            return
        self.avatar.marker.setPos(point)
        self.avatar.set_destination(point)

    def game_loop(self, task):
        dt = globalClock.getDt()
        self.avatar.update(dt)

        # Update avatar z pos
        origin = Point3(
            self.avatar.nodepath.getX(), self.avatar.nodepath.getY(), 5)

        direction = Vec3(0, 0, -1)
        point = self.floor_picker.from_ray(
            origin, direction, condition=lambda o: o.getName() == 'Plane')
        if point:
            assert point.getX() == self.avatar.nodepath.getX()
            self.avatar.nodepath.setPos(point)

        return direct.task.Task.cont


w = World()
base.run()
