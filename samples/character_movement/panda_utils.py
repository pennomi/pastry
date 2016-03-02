from direct.showbase.DirectObject import DirectObject
from panda3d.core import CollisionRay, CollisionTraverser, GeomNode, \
    CollisionNode, Point3, Vec3, CompassEffect, CollisionHandlerQueue, Point2
from direct.task import Task
from direct.interval import LerpInterval as LERP


class RayPicker:
    _parent = None

    def __init__(self, debug=False):
        if self._parent is None:
            self._parent = render

        # Init components
        self._traverser = CollisionTraverser()
        self._handler = CollisionHandlerQueue()
        self._node = CollisionNode('picker_ray')
        self._nodepath = self._parent.attachNewNode(self._node)
        self._ray = CollisionRay()

        # Set up relationships
        self._node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self._node.addSolid(self._ray)
        self._traverser.addCollider(self._nodepath, self._handler)

        # Show collisions?
        if debug:
            self._traverser.showCollisions(render)

    def _iterate(self, condition):
        # TODO: Move condition to the constructor
        # Iterate over the collisions and pick one
        self._traverser.traverse(render)

        # Go closest to farthest
        self._handler.sortEntries()

        for i in range(self._handler.getNumEntries()):
            pickedObj = self._handler.getEntry(i).getIntoNodePath()
            # picker = self.handler.getEntry(i).getFromNodePath()

            if not condition or (condition and condition(pickedObj)):
                point = self._handler.getEntry(i).getSurfacePoint(render)
                return point

        # Too bad, didn't find any matches
        return None

    def from_ray(self, origin, direction, condition=None):
        # Set the ray from a specified point and direction
        self._ray.setOrigin(origin)
        self._ray.setDirection(direction)
        return self._iterate(condition)


class MouseRayPicker(RayPicker):
    def __init__(self):
        self._parent = camera
        super().__init__()

    def from_mouse(self, condition=None):
        # Get the mouse and generate a ray form the camera to its 2D position
        mouse = base.mouseWatcherNode.getMouse()
        self._ray.setFromLens(base.camNode, mouse.getX(), mouse.getY())
        return self._iterate(condition)


def clamp(v, minmax):
    minimum, maximum = minmax
    return max(minimum, min(v, maximum))


class EdgeScreenTracker(DirectObject):
    """Mouse camera control interface."""
    # TODO: Right click drag (trackball) stuff
    # TODO: Keyboard stuff

    def __init__(self, target, offset=Point3.zero(), initial_zoom=10,
                 zoom_limits=(2, 20), pitch_limits=(-80, -10)):
        super().__init__()
        base.disableMouse()
        self.zoom = initial_zoom
        self.speed = 1.0 / 20.0
        self.zoom_limits = zoom_limits
        self.pitch_limits = pitch_limits

        # Move the camera with the target
        self.target = target.attachNewNode('camera target')
        self.target.setPos(offset)

        # Though the camera parents to the avatar, lock its rotation to render
        self.target.node().setEffect(CompassEffect.make(render))
        camera.reparentTo(self.target)
        camera.setPos(0, -self.zoom, 0)
        self.rotate_camera(Point2(0, 0))
        self.accept('wheel_up', self.adjust_zoom, [0.7])
        self.accept('wheel_down', self.adjust_zoom, [1.3])
        # TODO: Polish up this keyboard movement (it's busted)
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
        mouse_pos = base.mouseWatcherNode.getMouse()
        if mouse_pos.getX() > 0.99:
            self.rotate_camera(Point2(-10, 0))
        elif mouse_pos.getX() < -0.99:
            self.rotate_camera(Point2(10, 0))
        if mouse_pos.getY() > 0.9:
            self.rotate_camera(Point2(0, -3))
        elif mouse_pos.getY() < -0.9:
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
