from direct.actor import Actor
from panda3d.core import NodePath


class Sinbad:
    def __init__(self):
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
            "Humerus.L", "Humerus.R",
            "Ulna.L", "Ulna.R",
            "Hand.L", "Hand.R",
        ]
        self._model.makeSubpart("top", top_parts, excludeJoints=bottom_parts)
        self._model.makeSubpart("bottom", bottom_parts, excludeJoints=top_parts)
        self._model.setHprScale(180, 0, 0, .2, .2, .2)
        self._model.reparentTo(self.nodepath)
        self.stand()

    def run(self):
        if self._model.getCurrentAnim() not in ["runTop", "runBottom"]:
            self._model.loop("runTop", partName="top")
            self._model.loop("runBottom", partName="bottom")

    def stand(self):
        # TODO: Sometimes this isn't getting triggered properly
        if not self._model.getCurrentAnim() == 'idle':
            self._model.loop("idle")
