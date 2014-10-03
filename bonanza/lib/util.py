from shapely.geometry.point import Point
from geoalchemy2.shape import from_shape, to_shape


def prefixed_keys(d, prefix):
    make_pair = lambda k, v: (k.split(prefix)[0], v)
    return dict(make_pair(k, v) for k, v in d.items() if k.startswith(prefix))


def geoproperty(name, type):
    if type.lower().strip() == 'point':
        return PointGeometryDescriptor(name)


class PointGeometryDescriptor(object):
    """descriptor for 2D point geometry"""

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, type=None):
        wkb = getattr(instance, self.name)
        return to_shape(wkb)

    def __set__(self, instance, v):
        p = Point(*v)
        setattr(instance, self.name, from_shape(p))


def Point_repr(point):
    p = [point.x, point.y]
    if point.has_z:
        p.append(point.z)

    return "<Point {}>".format(', '.join(map(str, p)))

Point.__repr__ = Point_repr
