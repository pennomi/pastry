# TODO: Roadmap:
# * Get Sinbad walking on the ground
# * Movement via targets and timestamps
# * Multiplayer via Pastry


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


# Mouse collider
PICKER_COLLISION_TRAVERSER = CollisionTraverser()
PICKER_COLLISION_HANDLER = CollisionHandlerQueue()
PICKER_NODE = CollisionNode('mouse_ray')
PICKER_NODEPATH = camera.attachNewNode(PICKER_NODE)
PICKER_NODE.setFromCollideMask(GeomNode.getDefaultCollideMask())
PICKER_RAY = CollisionRay()
PICKER_NODE.addSolid(PICKER_RAY)
PICKER_COLLISION_TRAVERSER.add_collider(PICKER_NODEPATH, PICKER_COLLISION_HANDLER)

# Floor collider
FLOOR_COLLISION_TRAVERSER = CollisionTraverser()
FLOOR_COLLISION_HANDLER = CollisionHandlerQueue()
FLOOR_NODE = CollisionNode('floor_ray')
FLOOR_NODEPATH = render.attachNewNode(FLOOR_NODE)
FLOOR_NODE.setFromCollideMask(GeomNode.getDefaultCollideMask())
FLOOR_RAY = CollisionRay()
FLOOR_NODE.addSolid(FLOOR_RAY)
FLOOR_COLLISION_TRAVERSER.add_collider(FLOOR_NODEPATH, FLOOR_COLLISION_HANDLER)


def clamp(v, minimum, maximum):
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
    def __init__(self, initial_position=Point3.zero(), speed=3):
        self.start_kf = Keyframe(initial_position, time=now())
        self.end_kf = Keyframe(initial_position, time=now())

        self.speed = speed  # moving speed
        self.vel = Vec3.zero()  # velocity

        # Avatar scene graph setup
        self.prime = NodePath('avatar prime')
        self.prime.reparentTo(render)  # Make Avatar visible.
        self.prime.setZ(5)  # Be sure to start above the floor.
        self.prime.setCollideMask(BitMask32.allOff())  # no collisions!

        # Prepare animation state
        self.myActor = Actor.Actor('models/Sinbad', {
            "runTop": "models/Sinbad-RunTop",
            "runBottom": "models/Sinbad-RunBase",
            "dance": "models/Sinbad-Dance.001",
            "idle": "models/Sinbad-IdleTop",
        })
        self.myActor.setHprScale(*(180, 0, 0, .2, .2, .2))
        self.myActor.reparentTo(self.prime)
        self.stand()

    def update(self, dt):
        # Calculate the position I should be based off of speed and time
        travel_vector = (self.end_kf.value - self.start_kf.value)
        percent_complete = 1 - (self.end_kf.time - now()) / (self.end_kf.time - self.start_kf.time)
        if percent_complete > 1:
            self.stand()
            return
        current_pos = self.start_kf.value + travel_vector * percent_complete
        self.prime.setX(current_pos.x)
        self.prime.setY(current_pos.y)

    def set_destination(self, point):
        ds = self.prime.get_pos() - point
        arrival_seconds = ds.length() / self.speed
        self.start_kf = Keyframe(self.prime.get_pos())
        self.end_kf = Keyframe(point, now() + arrival_seconds)
        self.run()

    def run(self):
        # TODO: Make Sinbad do half-body animations
        # actor.makeSubpart("legs", ["Left Thigh", "Right Thigh"])
        # actor.makeSubpart("torso", ["Head"], ["Left Thigh", "Right Thigh"])
        # actor.loop("walk", partName="legs")
        # actor.loop("reload", partName="torso")
        self.myActor.loop('runBottom')

    def stand(self):
        self.myActor.loop("idle")


class Environment:
    def __init__(self):
        self.prime = loader.loadModel("models/level1")
        self.prime.reparentTo(render)


class Marker:
    def __init__(self):
        # you probably want to use a different marker model
        self.prime = loader.loadModel('models/Sinbad')
        self.prime.reparentTo(render)
        self.prime.setScale(.05, .05, .05)
        self.prime.setCollideMask(BitMask32.allOff())


class EdgeScreenTracker(DirectObject):
    """Mouse camera control interface."""

    def __init__(self, avatar, offset=Point3.zero(), dist=10, rot=20,
                 zoom=(2, 20), pitch=(-80, -10)):
        super().__init__()
        base.disableMouse()
        self.zoomLvl = dist
        self.speed = 1.0 / rot
        self.zoomClamp = zoom
        self.clampP = pitch
        self.target = avatar.attachNewNode('camera target')
        self.target.setPos(offset)
        self.target.node().setEffect(CompassEffect.make(render))
        camera.reparentTo(self.target)
        camera.setPos(0, -self.zoomLvl, 0)
        self.rotateCam(Point2(0, 0))
        self.accept('wheel_up', self.cameraZoom, [0.7])
        self.accept('wheel_down', self.cameraZoom, [1.3])
        taskMgr.add(self.mousecam_task, "mousecam_task")

    def mousecam_task(self, task):
        self.setDist()
        camera.lookAt(self.target)
        if not base.mouseWatcherNode.hasMouse():
            return Task.cont

        # Handle border-panning
        mpos = base.mouseWatcherNode.getMouse()
        if mpos.getX() > 0.99:
            self.rotateCam(Point2(-10, 0))
        elif mpos.getX() < -0.99:
            self.rotateCam(Point2(10, 0))
        if mpos.getY() > 0.9:
            self.rotateCam(Point2(0, -3))
        elif mpos.getY() < -0.9:
            self.rotateCam(Point2(0, 3))
        return Task.cont  # loop again.

    def rotateCam(self, arc):
        newP = clamp(self.target.getP() - arc.getY(), *self.clampP)  # Clamped.
        newH = self.target.getH() + arc.getX()  # Not clamped, just added.
        LERP.LerpHprInterval(
            self.target, self.speed, Vec3(newH, newP, self.target.getR())
        ).start()

    def cameraZoom(self, zoomFactor, ):
        """Scale and clamp zoom level, then set distance by it."""
        self.zoomLvl = clamp(self.zoomLvl * zoomFactor, *self.zoomClamp)
        self.setDist()

    def setDist(self):
        """Maintain a constant distance to the target."""
        vec = camera.getPos()
        vec.normalize()
        vec *= self.zoomLvl
        camera.setFluidPos(vec)


class World(DirectObject):
    def __init__(self):
        super().__init__()
        self.avatar = Avatar()
        self.blorp = Environment()
        self.environ = self.blorp.prime
        self.marker = Marker().prime
        EdgeScreenTracker(self.avatar.prime, Point3(0, 0, 1))
        self.accept('mouse1', self.on_click)
        PICKER_COLLISION_TRAVERSER.showCollisions(render)
        taskMgr.add(self.game_loop, "game_loop")  # start the gameLoop task

    def on_click(self):
        """Handle the click event."""
        mouse = base.mouseWatcherNode.getMouse()
        PICKER_RAY.setFromLens(base.camNode, mouse.getX(), mouse.getY())

        PICKER_COLLISION_TRAVERSER.traverse(render)
        for i in range(PICKER_COLLISION_HANDLER.getNumEntries()):
            PICKER_COLLISION_HANDLER.sortEntries()  # get the closest object
            pickedObj = PICKER_COLLISION_HANDLER.getEntry(i).getIntoNodePath()
            picker = PICKER_COLLISION_HANDLER.getEntry(i).getFromNodePath()
            # For now all we care about is clicking on the ground
            # We could just ignore this check to get any clicked object
            if pickedObj.getName() == 'Plane':
                point = PICKER_COLLISION_HANDLER.getEntry(i).getSurfacePoint(render)
                self.marker.setPos(point)
                self.avatar.set_destination(point)
                break

    def game_loop(self, task):
        dt = globalClock.getDt()
        self.avatar.update(dt)

        # Update avatar z pos
        FLOOR_RAY.setOrigin(self.avatar.prime.getX(), self.avatar.prime.getY(), 6)
        FLOOR_RAY.setDirection(0, 0, -1)
        FLOOR_COLLISION_TRAVERSER.traverse(render)
        for i in range(FLOOR_COLLISION_HANDLER.getNumEntries()):
            FLOOR_COLLISION_HANDLER.sortEntries()  # get the closest object
            pickedObj = FLOOR_COLLISION_HANDLER.getEntry(i).getIntoNodePath()
            point = FLOOR_COLLISION_HANDLER.getEntry(i).getSurfacePoint(render)
            picker = FLOOR_COLLISION_HANDLER.getEntry(i).getFromNodePath()
            if pickedObj.getName() == 'Plane':
                self.avatar.prime.setZ(point.z)
                break

        return direct.task.Task.cont


w = World()
base.run()
