import unittest
from my_ss.common import *


class common_tester(unittest.TestCase):
    def test_int_to_bytes(self):
        self.assertEqual(addr_str_to_bytes(127), b'\x7f')
