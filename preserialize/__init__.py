"""Pre-serialize a (possibly cyclic) object graph to a simple tree."""

from __future__ import print_function

from collections import OrderedDict
import re
import sys

from fn.recur import stackless

__version__ = "2017.7"
IS_PYTHON2 = sys.version_info.major < 3
STR = unicode if IS_PYTHON2 else str
PRIMITIVE = int, float, STR
IDENTIFIER_PATTERN = r"[^\d\W]\w*"
TYPE_NAME_PATTERN = r"[{escape_char}]?([^\d\W]\w*)?([.][^\d\W]\w*)*"
DATA = u""


class PreserializeError(Exception):
    """Parent Exception for this module."""

    pass


class UnregisteredTypeError(PreserializeError):
    """Encountered unregistered type in object, or unknown type in data."""

    pass


def is_identifier(s):
    """Check if ``s`` is a valid Python identifier."""
    return re.fullmatch(IDENTIFIER_PATTERN, s, re.UNICODE)


def is_type_name(escape_char, s):
    """Check if ``s`` matches regex :const:`TYPE_NAME_PATTERN`."""
    return re.fullmatch(TYPE_NAME_PATTERN.format(escape_char=escape_char),
                        s, re.UNICODE)


def cast_int(s):
    """Cast ``s`` to an ``int`` if possible."""
    try:
        return int(s)
    except ValueError:
        return s


class Deconstructor(object):
    """Define object (de-)pre-serialization."""

    def __init__(self, cls, escape_char,
                 name=None, version=None, ignore=None):
        """Constructor.

        :param cls: Class to register this :class:`Deconstructor` to.
        :type cls: class

        :param escape_char: Escape character.
        :type escape_char: str

        :param name: Type name in output data.
        :type name: str

        :param version: Version identifier.
        :type version: int, str

        :param ignore: Don't serialise these object *attribute* names.
        :type ignore: list
        """
        self.cls = cls
        self.name = cls.__name__.lower() if name is None else name
        if not is_type_name(escape_char, self.name):
            raise PreserializeError(
                u'Cannot use "{0}" as type name.'.format(self.name))
        self.version = version
        self.ignore = set(ignore) if ignore else set()

    def deconstruct(self, obj):
        """List of sequence values and dict of *key* to *attribute* in `obj`.

        :param obj: Object to pre-serialize.
        :type obj: object

        :returns: Pair of args, kwargs {*key* : *attribute*} suitable
                  for :meth:`construct`. Either can be ``None``.
        :rtype: list x dict

        """
        return None, None

    def construct(self, args, kwargs):
        """De-pre-serialize class from ``args`` and ``kwargs``.

        :param args: Constructor args. If ``None``, use ``__new__``,
                     else ``__init__``.
        :type args: list

        :param kwargs: Dictionary of *key* to *attribute* value.
        :type kwargs: dict

        :returns: Object instance.
        :rtype: object
        """
        obj = self.cls(*args) if args else self.cls.__new__(self.cls)
        if kwargs:
            for key, value in kwargs.items():
                self.setattr(obj, key, value)
        return obj

    def setattr(self, obj, key, value):
        """Set attribute of ``obj`` at ``key`` to ``value``.

        :param obj: The object.
        :type obj: object

        :param key: The *key* representing the *attribute*.
        :type key: str
        """
        raise PreserializeError(u"Not implemented.")


class IterableDeconstructor(Deconstructor):
    """Deconstructor for a sequence class such as ``tuple`` or ``set``."""

    def deconstruct(self, obj):
        return list(obj), None  # unpack single list item

    def construct(self, args, kwargs):
        return super().construct((args,), kwargs)  # repack

    def setattr(self, obj, key, value):
        obj[key] = value


class DictDeconstructor(Deconstructor):
    """Deconstructor for a ``dict``. Uses kwargs if possible."""

    def deconstruct(self, obj):
        if all(isinstance(key, STR) and is_identifier(key)
               for key in obj.keys()):
            return None, obj
        else:
            return list(list(item) for item in obj.items()), None  # unpack

    def construct(self, args, kwargs):
        return super().construct((args,), kwargs)  # repack

    def setattr(self, obj, key, value):
        obj[key] = value


class InstanceDeconstructor(Deconstructor):
    """Deconstructor for a class instance. Uses ``vars()``."""

    def deconstruct(self, obj):
        return None, dict((key, value) for key, value in vars(obj).items()
                          if key not in self.ignore)

    def setattr(self, obj, key, value):
        vars(obj)[key] = value


BASIC_TYPES = (
    (int,),
    (float,),
    (STR,),
    (tuple, IterableDeconstructor),
    (set, IterableDeconstructor))


class LinkManager(object):
    """
    Tracks each *link*, defines and manages *reference* objects.

    The first character of :attr:`KEY` is used as the escape character.
    """

    KEY = u""

    def __init__(self):
        self._path_cache = {}  # id(obj) -> path
        self._object_cache = {}  # path -> obj
        self._links = OrderedDict()  # dest -> [i, [source, ...]]
        self._parent_deconstructors = dict()  # path -> Deconstructor

    @classmethod
    def escape_char(cls):
        """Return the first character of :attr:`KEY`."""
        return cls.KEY[0]

    def path_cache_add(self, obj, path):
        """For pre-serialization, add ``obj`` -> ``path`` to cache."""
        self._path_cache[id(obj)] = path

    def path_cache_get(self, obj):
        """Return the ``path`` for ``obj``."""
        return self._path_cache[id(obj)]

    def object_cache_add(self, path, obj):
        """For de-pre-serialization, add ``path`` -> ``obj`` to cache."""
        self._object_cache[path] = obj

    def object_cache_get(self, path):
        """Return the object for ``path``."""
        return self._object_cache[path]

    def is_ref(self, obj):
        """Check if ``obj`` is a reference matching :meth:`make_ref`."""
        raise Exception(u"Not implemented")

    def make_ref(self, path):
        """Return reference for ``path``."""
        raise Exception(u"Not implemented")

    def ref_path(self, ref):
        """Return the *path* underlying ``ref``."""
        raise Exception(u"Not implemented")

    def add(self, source, dest):
        """Add a link from ``source`` to ``dest``."""
        if dest not in self._links:
            self._links[dest] = [len(self._links), []]
        self._links[dest][1].append(source)

    def set_source_parent_deconstructor(self, path, deconstructor):
        self._parent_deconstructors[path] = deconstructor

    def label_destination(self, i, obj):
        """Return labelled object to replace destination ``obj``."""
        return obj

    def unlabel_destination(self, obj):
        """Return object underlying labelled ``obj``."""
        return obj

    def getitem(self, data, path):
        """Get datum at ``path`` in ``data``."""
        for key in path:
            if self.is_ref(data):
                data = self.unlabel_destination(data)
            data = data[key]
        return data

    def setitem(self, data, path, value):
        """Set datum at ``path`` in ``data`` to ``value``."""
        data = self.getitem(data, path[:-1])
        key = path[-1]
        if self.is_ref(data):
            data = self.unlabel_destination(data)
        data[key] = value
        return data

    def label_data(self, data):
        """Label each destination in ``data``."""
        for dest, (i, sources) in self._links.items():
            if dest:
                self.setitem(data, dest, self.label_destination(
                    i, self.getitem(data, dest)))
            else:
                data = self.label_destination(i, data)
        return data

    def set_sources(self, obj):
        """For each *reference* in ``obj``, replace source with destination."""
        for dest, (i, sources) in self._links.items():
            dest_obj = self.object_cache_get(dest)
            for source in sources:
                deconstructor = self._parent_deconstructors[source]
                parent_obj = self.object_cache_get(source[:-1])
                key = source[-1]
                if deconstructor:
                    deconstructor.setattr(parent_obj, key, dest_obj)
                else:
                    parent_obj[key] = dest_obj


class Preserializer(object):
    """A ``Preserializer`` instance handles the (de)-pre-serialization."""

    TYPE = u"{escape_char}type"
    VERSION = u"{escape_char}version"

    def __init__(self, types, link_manager_cls,
                 list_type=list, mapping_type=dict, key_encoder=None):
        """Constructor.

        :param types: Table of (cls, deconstructor, kwargs) to register.
        :type types: sequence

        :param link_manager_cls: The :class:`LinkManager` subclass to use.
        :type link_manager_cls: type

        :param list_type: The class to use for a list output.
        :type list_type: type

        :param mapping_type: The class to use for a *mapping* output.
        :type mapping_type: type

        :param key_encoder: Transform each *mapping* *key*.
        :type key_encoder: Encoder
        """
        self.link_manager_cls = link_manager_cls
        self.list_type = list_type
        self.mapping_type = mapping_type

        self.escape_char = link_manager_cls.escape_char()
        escape_encoder = IdentifierEscapeEncoder(self.escape_char)
        self.encoder = (key_encoder.compose(escape_encoder) if key_encoder
                        else escape_encoder)

        self.type_key = self.TYPE.format(escape_char=self.escape_char)
        self.version_key = self.VERSION.format(escape_char=self.escape_char)

        self.deconstructors = {}  # (type, version) -> Deconstructor
        self.versions = {}        # type -> version
        self.types = {}           # (name, version) -> type

        self.register_types(types)

    def register(self, cls, deconstructor_cls=InstanceDeconstructor, **kwargs):
        """Register a type with a :class:`Deconstructor`.

        :param cls: The type to register.
        :type cls: type

        :param deconstructor_cls: The :class:`Deconstructor` to
                           associate with ``cls``. If ``None``, then
                           ``cls`` pre-serializes to itself.
        :type deconstructor_cls: None, type

        :param kwargs: Arguments to pass through to the :class:`Deconstructor`.

        """
        if deconstructor_cls:
            deconstructor = deconstructor_cls(cls, self.escape_char, **kwargs)
            version = deconstructor.version
            self.types[deconstructor.name, version] = cls
        else:
            deconstructor = None
            version = None

        self.deconstructors[cls, version] = deconstructor

        if version is not None:
            self.versions[cls] = version

    def register_types(self, types):
        """Call :meth:`register` for each row in ``types``."""
        for row in types:
            n = len(row)
            if n == 1:
                cls, = row
                deconstructor_cls = None
                kwargs = {}
            elif n == 2:
                cls, deconstructor_cls = row
                kwargs = {}
            else:
                cls, deconstructor_cls, kwargs = row
            self.register(cls, deconstructor_cls, **kwargs)

    def get_deconstructor_from_type(self, t):
        """Return suitable :class:`Deconstructor` for ``t``.

        :returns: The matching :class:`Deconstructor` for ``t``.
        :rtype: Deconstructor
        """
        try:
            return self.deconstructors[t, self.versions.get(t)]
        except KeyError:
            raise UnregisteredTypeError(
                format(u"Cannot pre-serialize {0}".format(t.__name__)))

    def get_deconstructor_from_data(self, data):
        """Return suitable :class:`Deconstructor` for ``data``.

        :returns: The matching :class:`Deconstructor` based on :attr:`type_key`
                  and :attr:`version_key`.
        :rtype: Deconstructor
        """
        version = data.get(self.version_key)
        try:
            t = self.types.get((data[self.type_key], version))
            return self.deconstructors[t, version]
        except KeyError:
            raise UnregisteredTypeError(
                format(u"Cannot de-pre-serialize {0} version: {1}".format(
                    data[self.type_key], version)))

    def deconstructor(self, cls, **kwargs):
        """Return convenience class decorator for a :class:`Deconstructor`.

        :param kwargs: Arguments to pass through to the :class:`Deconstructor`.
        """
        def wrap(deconstructor_cls):
            self.register(cls, deconstructor_cls, **kwargs)
            return deconstructor_cls
        return wrap

    def preserialize(self, obj):
        """Pre-serialize ``obj``.

        :param obj: The object to pre-serialize.
        :type obj: object

        :returns: Data corresponding to ``obj``.
        :rtype: basic
        """
        link_manager = self.link_manager_cls()
        data = self._preserialize(self, obj, (), link_manager)
        data = link_manager.label_data(data)  # can change top datum
        return data

    def depreserialize(self, data):
        """De-pre-serialize object from pre-serialized data.

        :param data: The data to de-pre-serialize.
        :type data: basic

        :returns: Object created from ``data``.
        :rtype: object
        """
        link_manager = self.link_manager_cls()
        obj = self._depreserialize(self, data, (), data, link_manager, None)
        link_manager.set_sources(obj)
        return obj

    @stackless
    def _preserialize(self, obj, path, link_manager):
        t = type(obj)

        if t != list:
            deconstructor = self.get_deconstructor_from_type(t)
            if deconstructor is None:
                yield obj
                return

        try:
            dest_path = link_manager.path_cache_get(obj)
            link_manager.add(path, dest_path)
            yield link_manager.make_ref(dest_path)
            return
        except KeyError:
            pass

        link_manager.path_cache_add(obj, path)

        if t == list:
            data = self.list_type()
            for i, item in enumerate(obj):
                data.append((yield self._preserialize.call(
                    self, item, path + (i,), link_manager)))
        else:
            data = self.mapping_type()
            data[self.type_key] = deconstructor.name
            if deconstructor.version is not None:
                data[self.version_key] = deconstructor.version

            args, kwargs = deconstructor.deconstruct(obj)
            if args:
                data[DATA] = self.list_type()
                for i, arg in enumerate(args):
                    data[DATA].append((yield self._preserialize.call(
                        self, arg, path + (DATA, i), link_manager)))

            if kwargs:
                for key, attr in kwargs.items():
                    ekey = self.encoder.encode(key)
                    data[ekey] = yield self._preserialize.call(
                        self, attr, path + (ekey,), link_manager)
        yield data

    @stackless
    def _depreserialize(self, data, path, doc, link_manager,
                        parent_deconstructor):
        t = type(data)

        if t != self.list_type and t != self.mapping_type:
            deconstructor = self.get_deconstructor_from_type(t)
            if deconstructor is None:
                yield data
                return

        if link_manager.is_ref(data):
            dest_path = tuple(cast_int(key)
                              for key in link_manager.ref_path(data)
                              if key != DATA)

            try:
                yield link_manager.object_cache_get(dest_path)
                return
            except KeyError:
                pass

            link_manager.add(path, dest_path)
            link_manager.set_source_parent_deconstructor(
                path, parent_deconstructor)
            yield data
            return

        if t == self.list_type:
            obj = []
            for i, item in enumerate(data):
                obj.append((yield self._depreserialize.call(
                    self, item, path + (i,), doc, link_manager, None)))
        else:
            deconstructor = self.get_deconstructor_from_data(data)
            args = []
            kwargs = {}
            for key, item in data.items():
                if key == DATA:
                    for i, arg in enumerate(item):
                        args.append((yield self._depreserialize.call(
                            self, arg, path + (i,), doc, link_manager,
                            deconstructor)))
                elif key not in {self.type_key, self.version_key}:
                    dkey = self.encoder.decode(key)
                    kwargs[dkey] = yield self._depreserialize.call(
                        self, item, path + (dkey,), doc, link_manager,
                        deconstructor)
            obj = deconstructor.construct(args, kwargs)
        link_manager.object_cache_add(path, obj)
        yield obj


class Encoder(object):
    """Bijectively encode and decode strings."""

    def encode(self, s):
        return s

    def decode(self, s):
        return s

    def compose(self, encoder):
        """Create a :class:`ComposedEncoder` of ``self`` and ``encoder``."""
        return ComposedEncoder(self, encoder)


class ComposedEncoder(Encoder):
    """Compose two encoders, operating right-to-left."""

    def __init__(self, encoder_b, encoder_a):
        self.encoder_a = encoder_a
        self.encoder_b = encoder_b

    def encode(self, s):
        return self.encoder_b.encode(self.encoder_a.encode(s))

    def decode(self, s):
        return self.encoder_a.decode(self.encoder_b.decode(s))


class DoubleQuoteEncoder(Encoder):
    r"""Replace ``\`` with ``\\`` then ``"`` with ``\"``."""

    @classmethod
    def encode(cls, s):
        return u'"{0}"'.format(s.replace(u"\\", u"\\\\").replace(u'"', u'\\"'))

    @classmethod
    def decode(self, s):
        return s[1:-1].replace(u'\\"', u'"').replace(u"\\\\", u"\\")


class IdentifierEscapeEncoder(Encoder):
    """Check if string is identifier, and escape using escape character."""

    def __init__(self, char):
        """Constructor.

        :param char: The escape character.
        :type char:
        """
        self.char = char

    def encode(self, s):
        """Check ``s`` is a valid Python identifier and :attr:`char`-escape.

        :param s: The string to escape.
        :type s: str

        :returns: The escaped string.
        :rtype: str
        """
        s = STR(s)
        if is_identifier(s):
            return self.char if s == DATA else s.replace(self.char,
                                                         self.char*2)
        raise PreserializeError(u"Not a valid key name: {0!r}".format(s))

    def decode(self, s):
        """Undo ``char``-escaping.

        :param s: The escaped string.
        :type s: str

        :returns: The unescaped string.
        :rtype: str
        """
        return DATA if s == self.char else s.replace(self.char*2, self.char)
