Pre-serialize
=============

Customisable, versioned, stackless, cyclic object graph
pre-serializer.

The main point of this is that circular references are supported and
deep structures will not overflow the stack as we use a trampoline via
``@recur.stackless()`` from ``fn.py``. Also a Python ``dict``
containing arbitrary cyclic objects is correctly handled.
