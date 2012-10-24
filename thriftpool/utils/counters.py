import sys


class Average(object):
    """Count average without overflow."""

    def __init__(self):
        self.average = 0.0
        self.count = 0

    def add(self, x):
        self.count += 1
        self.average += (x - self.average) / self.count

    def __float__(self):
        return self.average

    def __int__(self):
        return int(self.average)

    def __repr__(self):
        return repr(self.average)


class Counter(object):
    """Counter without overflow."""

    def __init__(self):
        self.i = 0
        self.overflow = 0
        self.max = sys.maxint

    @property
    def val(self):
        return self.i + self.overflow * self.max

    def __iadd__(self, other):
        other = int(other)
        if self.i < self.max - other:
            self.i += other
        else:
            self.overflow += 1
            self.i = self.i + other - self.max
        return self

    def __int__(self):
        return self.val

    def __repr__(self):
        return repr(self.val)
