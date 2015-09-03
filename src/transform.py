from __future__ import division, print_function
import math
import unittest


def __mult(t0, t1):
    return t0.mult(t1)


class Transform(object):
    def __init__(self, m):
        self.m = tuple(m)

    def entry(self, x, y):
        return self.m[y * 3 + x]

    def x(self):
        return self.m[6]

    def y(self):
        return self.m[7]

    def mult(self, o):
        m = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(3):
            for j in range(3):
                m[j * 3 + i] = sum([self.entry(i, k) * o.entry(k, j) for k in range(3)])
        return Transform(m)

    def mult_point(self, p):
        t = self.mult(translate(p[0], p[1]))
        toreturn = [t.x(), t.y()]
        if len(p) == 3:
            toreturn.append(0)
        return tuple(toreturn)


class TransformTest(unittest.TestCase):
    def testEntry(self):
        t = Transform((1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEquals(1, t.entry(0, 0))
        self.assertEquals(4, t.entry(0, 1))
        self.assertEquals(7, t.entry(0, 2))
        self.assertEquals(2, t.entry(1, 0))
        self.assertEquals(5, t.entry(1, 1))
        self.assertEquals(8, t.entry(1, 2))
        self.assertEquals(3, t.entry(2, 0))
        self.assertEquals(6, t.entry(2, 1))
        self.assertEquals(9, t.entry(2, 2))

    def testMult(self):
        t0 = translate(1, 2)
        t1 = translate(10, 20)
        t2 = t0.mult(t1)
        self.assertEquals(translate(11, 22).m, t2.m)

    def testTranslatePoint(self):
        p0 = (11, 22)
        t = translate(10, 20)
        p1 = t.mult_point(p0)
        self.assertEquals((21, 42), p1)

    def testRotatePoint(self):
        p0 = (3, 4)
        t = rotate(90)
        p1 = t.mult_point(p0)
        self.assertAlmostEquals(-4, p1[0])
        self.assertAlmostEquals(3, p1[1])


IDENTITY = Transform([1, 0, 0, 0, 1, 0, 0, 0, 1])


def matrix(a, b, c, d, e, f):
    return Transform([a, b, 0, c, d, 0, e, f, 1])


def translate(x, y):
    return matrix(1, 0, 0, 1, x, y)


def scale(x, y=None):
    if y is None:
        y = x
    return matrix(x, 0, 0, y, 0, 0)


def skew_x(a):
    tana = math.tan(a)
    return matrix(1, 0, tana, 1, 0, 0)


def skew_y(a):
    tana = math.tan(a)
    return matrix(1, tana, 0, 1, 0, 0)


def rotate(a, p=None):
    r = math.radians(a)
    sina = math.sin(r)
    cosa = math.cos(r)
    transform = matrix(cosa, sina, -sina, cosa, 0, 0)

    if p is not None:
        x = p[0]
        y = p[1]
        inner = translate(-x, -y)
        outer = translate(x, y)
        transform = outer.mult(transform.mult(inner))

    return transform


def parse(transform_string):
    transform_strings = [s+")" for s in transform_string.split(")") if s.strip()]
    transforms = [eval(t) for t in transform_strings]
    return reduce(__mult, transforms)


class __TestParse(unittest.TestCase):
    def testOneTranslate(self):
        actual = parse("translate(10,20)")
        expected = translate(10, 20)
        self.assertEquals(expected.m, actual.m)

    def testTranslateTranslate(self):
        actual = parse("translate(10,0) translate(0,20)")
        expected = translate(10, 20)
        self.assertEquals(expected.m, actual.m)

if __name__ == "__main__":
    unittest.main()
