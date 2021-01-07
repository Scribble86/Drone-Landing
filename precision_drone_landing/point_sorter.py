
class PointSorter:
    """
    This class, written by Colin and documented by Nikita, takes an unsorted iterable containing two element iterables
    and sorts these points so they are in counter-clockwise order starting at the bottom left. This ordering is required
    for the python package shapely to create valid shapes using points. External access is managed through the
    sortPoints function.
    """
    def _angle_compare(self, p0, a, b):
        left = self._is_left(p0, a, b)
        if left == 0:
            return self._dist_compare(p0, a, b)
        return left > 0

    def _is_left(self, p0, a, b):
        return (a[0] - p0[0]) * (b[1] - p0[1]) - (b[0] - p0[0]) * (a[1] - p0[1])

    def _dist_compare(self, p0, a, b):
        distA = (p0[0] - a[0]) ** 2 + (p0[1] - a[1]) ** 2
        distB = (p0[0] - b[0]) ** 2 + (p0[1] - b[1]) ** 2
        return distA - distB < 0

    def _insertion_sort(self, p0, pointList):
        for index in range(1, len(pointList)):
            currentValue = pointList[index]
            currentPosition = index

            while currentPosition > 0 and self._angle_compare(p0, pointList[currentPosition - 1], currentValue):
                pointList[currentPosition] = pointList[currentPosition - 1]
                currentPosition = currentPosition - 1

            pointList[currentPosition] = currentValue
        return pointList

    def sort_points(self, points):
        y = min(list(map(lambda p: p[1], points)))
        x = max(list(map(lambda p: p[0], filter(lambda p: p[1] == y, points))))
        p0 = (x, y)
        sortedPoints = self._insertion_sort(p0, points)

        return sortedPoints
