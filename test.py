import unittest

from preserialize.json import JsonPreserializer


class JsonTests(unittest.TestCase):
    def setUp(self):
        self.preserializer = JsonPreserializer()

        class Parrot(object):
            def __init__(self, is_dead=True, from_egg=None):
                self.is_dead = is_dead
                self.from_egg = from_egg

        self.preserializer.register(Parrot, version=2)

        class Egg(object):
            def __init__(self, from_parrot=None):
                self.from_parrot = from_parrot

        self.preserializer.register(Egg)

        self.parrot = Parrot()
        self.parrot.from_egg = Egg(from_parrot=self.parrot)

    def test_int(self):
        obj = result = 123
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_int_de(self):
        obj = result = 123
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_float(self):
        obj = result = 3.1415927
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_float_de(self):
        obj = result = 3.1415927
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_str(self):
        obj = result = u'The Knights who say "Ni!".'
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_str_de(self):
        obj = result = u'The Knights who say "Ni!".'
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_bool(self):
        obj = result = False
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_bool_de(self):
        obj = result = False
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_none(self):
        obj = result = None
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_none_de(self):
        obj = result = None
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_list(self):
        obj = result = [123, 3.1415927, u'The Knights who say "Ni!".', False, None]
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_list_de(self):
        obj = result = [123, 3.1415927, u'The Knights who say "Ni!".', False, None]
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_dict(self):
        obj = {'brian': 'naughty boy'}
        result = {'$type': 'dict', 'brian': 'naughty boy'}
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_dict_de(self):
        obj = {'$type': 'dict', 'brian': 'naughty boy'}
        result = {'brian': 'naughty boy'}
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_dict_args(self):
        obj = {'brian': 'naughty boy', 3: 'Antioch'}
        result = {'$type': 'dict', '': [['brian', 'naughty boy'],
                                        [3, 'Antioch']]}
        self.assertEqual(self.preserializer.preserialize(obj), result)

    def test_dict_args_de(self):
        result = {'brian': 'naughty boy', 3: 'Antioch'}
        obj = {'$type': 'dict', '': [['brian', 'naughty boy'],
                                        [3, 'Antioch']]}
        self.assertEqual(self.preserializer.depreserialize(obj), result)


    def test_dict_args_cyclic(self):
        obj = {'brian': 'naughty boy', 3: 'Antioch', 'ouroboros': self.parrot}
        result = {"$type": "dict",
                  "": [["brian", "naughty boy"],
                       [3, "Antioch"],
                       ["ouroboros", {"$type": "parrot", "$version": 2,
                                      "is_dead": True,
                                      "from_egg": {"$type": "egg",
                                                   "from_parrot": {"$ref": "#//2/1"}}}]]}
        self.assertEqual(self.preserializer.preserialize(obj), result)
