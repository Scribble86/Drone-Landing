import threading


class LandingZone:
    """The LandingZone class contains data extracted from image recognition
    including the x,y,z distance estimations, the layer number, and the
    message embedded in the code. This is designed to store data
    extracted from a single frame of capture. This class is also
    thread-safe if multi-threading is implemented at a later date."""
    X = None
    Y = None
    Z = None
    Layer = None
    Code = None

    def __init__(self, layer, code, x, y, z):
        self._lock = threading.Lock()
        self._X = x
        self._Y = y
        self._Z = z
        self._Layer = layer
        self._Code = code

    def getPosition(self):
        """Return a position estimate.

        The estimate is a three-element tuple containing the (x,y,z)
        position estimation contained in this LandingZone object.
        """
        with self._lock:
            position = (self._X, self._Y, self._Z)
        return position

    def getLayer(self):
        """Return the layer that the position estimate was made from.

        Layers are:
            0 = outer
            1 = middle
            2 = inner"""
        with self._lock:
            layer = self._Layer
        return layer

    def print(self):
        """A debugging function to allow the LandingZone object to print debug output.
        """
        with self._lock:
            print("Layer:", self.Layer, "Code:", self.Code, "Position(", "X:", self.X, "Y:", self.Y, "Z:", self.Z, ")")


class TargetHandler:
    """TargetHandler is designed to be a thread-safe accessor and
    repository for the most recent position data available,
    in the form of LandingZone objects. It stores up to three
    of these, one for each layer in the landing pad."""
    def __init__(self):
        self.__lock = threading.Lock()
        self.__targets = [None, None, None]

    def update(self, newTargets):
        """Receive a batch of new LandingZone objects.

        This replaces any previous ones."""
        with self.__lock:
            self.__targets = newTargets
        return

    def get_target(self, index):
        """Return the LandingZone object with the specified index.

        Returns None otherwise."""
        with self.__lock:
            target = None
            if self.__targets[index] is not None:
                target = self.__targets[index]
        return target
