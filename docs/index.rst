Welcome to Preserialize's documentation!
========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Customisable, versioned, stackless, cyclic object graph
pre-serializer.

We input a Python object graph and output an object-free tree
consisting only of *basic* types, whilst preserving information about
the reference structure.

This simplified output can then easily and unambiguously be serialized
using your favourite libraries such as ``json`` or ``msgpack``.

Pointers and references follow the `JSON Pointer
<https://tools.ietf.org/html/rfc6901>`_ and `JSON Reference
<https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-02>`_
specifications.

The main point of this is that circular references are supported and
deep structures will not overflow the stack as we use a trampoline via
``@recur.stackless()`` from ``fn.py``. Also a Python ``dict``
containing arbitrary cyclic objects is correctly handled.

Terminology used throughout the code:

* A *primitive* type is one of ``int``, ``float``, or ``str``
  (``unicode`` in Python 2).
* A *mapping* is a ``dict`` where each key is a ``str``.
* A *basic* type is *primitive* or a ``list`` or *mapping*.
* A Python *object* has an *attribute*.
* Output *data* has a unicode *key* mapping to an *item*.
* A *path* is a sequence of *keys*.
* A *link* is a pair of *paths*, the source and destination.

Key names in the output are escaped to make room for metadata keys.

Usage
-----

The logic resides in :class:`preserializer.Preserializer` but a
concrete subclass is provided:
:class:`preserializer.json.JsonPreserializer`, suitable for
serialization to JSON.

A :class:`preserialize.Preserializer` class::

  from preserialize.json import JsonPreserializer
  preserializer = JsonPreserializer()

provides :meth:`preserialize.Preserializer.preserialize()`::

  data = preserializer.preserialize(obj)

and :meth:`preserialize.Preserializer.depreserialize()`::

  obj = preserializer.depreserialize(data)

and the resulting data can be serialized::

  s = json.dumps(data)

including using serializers that cannot handle objects, cyclic
references, or deep structures.

You must explicitly register a type, ensuring you catch everying in
the object graph (`PEP20
<https://www.python.org/dev/peps/pep-0020/>`_: explicit is better than
implicit).

Use a :class:`preserialize.Deconstructor` subclass for precise control
of pre-serializing. The default
:class:`preserialize.InstanceDeconstructor` uses ``__new__()`` and
``vars()``.

Anything that can sensibly be coerced to, and constructed from a
``list`` can be serialized using ``IterableDeconstructor``::

  preserializer.register(set, prepickle.IterableDeconstructor)

Extra ``Deconstructors`` are included in submodules. For example, the
``builtins.TypeDeconstructor`` can be used to serialize functions::

  preserializer.register(types.FunctionType, prepickle.builtins.TypeDeconstructor)

and another custom ``Deconstructor`` is used for ``weakref.WeakrefDeconstructor``::

  preserializer.register(weakref.ref, prepickle.weakref.WeakrefDeconstructor)

Examples
--------

An ``int``, ``float`` or ``str`` pre-serializes to itself. JSON is
also natively able to handle ``None`` and ``bool``.

Instances
`````````

A simple use case of a user (new-style in Python 2) class and default
``Deconstructor``::

  class Parrot(object):
      def __init__(self, is_alive=False):
          self.is_alive = is_alive

  preserializer.register(Parrot)

Then:

+--------------------+---------------------------------------------------------+
|Object              |.. code-block:: python                                   |
|                    |                                                         |
|                    |  Parrot(is_alive=False)                                 |
+--------------------+---------------------------------------------------------+
|JsonPreserializer   |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'$type': 'parrot', 'is_alive': False}                 |
+--------------------+---------------------------------------------------------+
|JSON                |.. code-block:: json                                     |
|                    |                                                         |
|                    |  {"$type": "parrot", "is_alive": false}                 |
+--------------------+---------------------------------------------------------+

Versioned
`````````

It is good practice to add a version number to serialized data::

  preserializer.register(Parrot, version=1)

gives:

+--------------------+---------------------------------------------------------+
|Object              |.. code-block:: python                                   |
|                    |                                                         |
|                    |  Parrot(is_alive=False)                                 |
+--------------------+---------------------------------------------------------+
|JsonPreserializer   |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'$type': 'parrot', '$version': 1, 'is_alive': False}  |
+--------------------+---------------------------------------------------------+
|JSON                |.. code-block:: json                                     |
|                    |                                                         |
|                    |  {"$type": "parrot", "$version": 1, "is_alive": false}  |
+--------------------+---------------------------------------------------------+

and then if we modify the class later::

  class Parrot(object):
      def __init__(self, is_dead=True, from_egg=None):
          self.is_dead = is_dead
          self.from_egg = from_egg

  preserializer.register(Parrot, version=2)

we get:

.. code-block:: json

  {"$type": "parrot", "$version": 2, "is_dead": true, "from_egg": null}

and when loading, if both classes are registered, for example as above
and also::

  preserializer.register(LegacyParrot, name="parrot", version=1)

then loading mixed version data will instantiate the correct classes.

Cyclic
``````

Extending the case above to include a cyclic reference::

  class Egg(object):
      def __init__(self, from_parrot=None):
          self.from_parrot = from_parrot

  preserializer.register(Egg)

  parrot = Parrot()
  parrot.from_egg = Egg(from_parrot=parrot)

so dumping gives:

.. code-block:: json

  {"$type": "parrot", "$version": 2,
   "is_dead": true,
   "from_egg": {"$type": "egg",
                "from_parrot": {"$ref": "#"}}}

containing a JSON Reference pointing to the top-level object.

Dictionary
``````````

JSON does not natively support Python's ``dict``, so we pre-serialize
like an instance.

+--------------------+---------------------------------------------------------+
|Object              |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {}                                                     |
+--------------------+---------------------------------------------------------+
|JsonPreserializer   |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'$type': 'dict'}                                      |
+--------------------+---------------------------------------------------------+
|JSON                |.. code-block:: json                                     |
|                    |                                                         |
|                    |  {"$type": "dict"}                                      |
+--------------------+---------------------------------------------------------+

If a ``dict`` is a *mapping*, we can use a JSON object:

+--------------------+---------------------------------------------------------+
|Object              |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'brian': 'naughty boy'}                               |
+--------------------+---------------------------------------------------------+
|JsonPreserializer   |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'$type': 'dict', 'brian': 'naughty boy'}              |
+--------------------+---------------------------------------------------------+
|JSON                |.. code-block:: json                                     |
|                    |                                                         |
|                    |  {"$type": "dict", "brian": "naughty boy"}              |
+--------------------+---------------------------------------------------------+

But if any key is not a valid identifier, we pre-serialize as if it
contained an empty key referencing an association list, so the type of
keys is preserved and included in the object graph:

+--------------------+---------------------------------------------------------+
|Object              |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'brian': 'naughty boy', 3: 'Antioch'}                 |
+--------------------+---------------------------------------------------------+
|JsonPreserializer   |.. code-block:: python                                   |
|                    |                                                         |
|                    |  {'$type': 'dict', '': [['brian', 'naughty boy'],       |
|                    |                         [3, 'Antioch']]}                |
+--------------------+---------------------------------------------------------+
|JSON                |.. code-block:: json                                     |
|                    |                                                         |
|                    |  {"$type": "dict", "": [["brian", "naughty boy"],       |
|                    |                         [3, "Antioch"]]}                |
+--------------------+---------------------------------------------------------+

Using the cyclic object from before::

  {'brian': 'naughty boy', 3: 'Antioch', 'ouroboros': parrot}

dumps to JSON:

.. code-block:: json

  {"$type": "dict",
   "": [["brian", "naughty boy"],
        [3, "Antioch"],
        ["ouroboros", {"$type": "parrot", "$version": 2,
                       "is_dead": true,
                       "from_egg": {"$type": "egg",
                                    "from_parrot": {"$ref": "#//2/1"}}}]]}

and note that the cyclic reference now descends into the ``dict``.


Limitations
-----------

We try to support Python 2, but you should use ``unicode`` and new-style
classes.


License
-------

Copyright James A. H. Skillen, 2017.

Distributed under the terms of the MIT license.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
