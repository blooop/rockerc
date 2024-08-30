from unittest import TestCase
from rockerc.basic_class import BasicClass


class TestBasicClass(TestCase):
    def test_init(self):
        instance = BasicClass()

        self.assertEqual(instance.int_var, 0)
