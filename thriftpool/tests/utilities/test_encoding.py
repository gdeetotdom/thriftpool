# -*- encoding: utf-8 -*-
from __future__ import absolute_import

from thriftpool.tests.utils import TestCase
from thriftpool.utils.encoding import smart_str, smart_unicode


class TestEncoding(TestCase):

    def setUp(self):
        super(TestEncoding, self).setUp()
        u_str = self.unicode_str = u'строка'
        self.encoded_unicode_str = u_str.encode('utf-8')
        b_str = self.bytes_str = 'строка'
        self.decoded_bytes_str = b_str.decode('utf-8')

    def test_smart_str(self):
        self.assertEqual(self.bytes_str, smart_str(self.decoded_bytes_str))
        self.assertIsInstance(smart_str(self.decoded_bytes_str), str)
        self.assertEqual(self.bytes_str, smart_str(self.bytes_str))
        self.assertIsInstance(smart_str(self.bytes_str), str)

    def test_smart_unicode(self):
        self.assertEqual(self.unicode_str,
                         smart_unicode(self.encoded_unicode_str))
        self.assertIsInstance(smart_unicode(self.encoded_unicode_str), unicode)
        self.assertEqual(self.unicode_str, smart_unicode(self.unicode_str))
        self.assertIsInstance(smart_unicode(self.unicode_str), unicode)
