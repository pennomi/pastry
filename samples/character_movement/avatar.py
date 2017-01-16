from panda3d.core import Point3, Vec3

from samples.character_movement.objects import Character
from samples.character_movement.panda_utils import RayPicker
from samples.character_movement.sinbad import Sinbad
from time import time as now


class Keyframe:
    """Track a value relative to some time. When multiple Keyframes are put
    together, you can create a lovely smooth path, even with network latency.
    """
    def __init__(self, value, time=None):
        self.value = value
        self.time = time or now()


class Avatar(Sinbad):
    speed = 3

    def __init__(self, distributed_object: Character, initial_position=Point3.zero()):
        # Save the actual game object to this instance
        self.do = distributed_object

        # TODO: Make into a list of keyframes to do waypoints
        # TODO: And this kind of info should live on the DO
        self.start_kf = Keyframe(initial_position, time=now())
        self.end_kf = Keyframe(initial_position, time=now())

        # show where the avatar is headed TODO: Use an arrow or something?
        self._marker = base.loader.loadModel('models/Sinbad')
        self._marker.reparentTo(base.render)
        self._marker.setScale(.05, .05, .05)

        super().__init__()

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

        # Update avatar z pos to snap to floor
        picker = RayPicker()  # TODO: Reuse instead of instantiating
        point = picker.from_ray(
            Point3(current_pos.x, current_pos.y, 5),
            Vec3(0, 0, -1),
            condition=lambda o: o.getName() == 'Plane')
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
