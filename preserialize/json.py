from jsonpointer import JsonPointer

from . import BASIC_TYPES, DictDeconstructor, LinkManager, Preserializer

JSON_TYPES = BASIC_TYPES + (
    (bool,),
    (type(None),),
    (dict, DictDeconstructor))


class JsonReferenceError(Exception):
    pass


class JsonReferenceLinkManager(LinkManager):
    "JSON Reference"

    KEY = u"$ref"

    def is_ref(self, obj):
        """Check if the object is a JSON Reference as per :func:`make_ref`.

        :param obj: The object to test.
        :type obj: object

        :returns: If ``obj`` looks like a JSON Reference.
        :rtype: bool
        """
        return isinstance(obj, dict) and len(obj) == 1 and self.KEY in obj

    def make_ref(self, dest):
        """Make a JSON Reference from a *path*.

        :param dest: Destination *path*.
        :type dest: *path*

        :returns: Dictionary mapping the key ``$ref`` to JSON Pointer.
        :rtype: dict
        """
        return {self.KEY: u"#{0}".format(JsonPointer.from_parts(dest).path)}

    def ref_path(self, ref):
        """Return the *path* inside the JSON Reference.

        :param ref: A JSON Reference as made by :meth:`make_ref`.
        :type ref: dict

        :returns: The destination *path*.
        :rtype: list
        """
        v = ref[self.KEY]
        if v.startswith(u"#"):
            return JsonPointer(v[1:]).parts
        raise JsonReferenceError(u"Unsupported reference: {0}".format(v))


class JsonPreserializer(Preserializer):
    def __init__(self):
        super().__init__(types=JSON_TYPES,
                         link_manager_cls=JsonReferenceLinkManager)
