from __future__ import absolute_import

import cPickle as pickle

from thriftpool.tests.utils import TestCase


class TestApp(TestCase):

    def test_pickling(self):
        self.app.loader.preload_modules()
        self.assertIn('ThriftPool', self.app.slots)
        buf = pickle.dumps(self.app)
        app = pickle.loads(buf)
        # ensure that slots serialized and loaded properly
        self.assertIn('ThriftPool', app.slots)
        # check configuration serialization
        self.assertEqual(dict(self.app.config), dict(app.config))
