import importlib

from .. import Deconstructor, STR


class TypeDeconstructor(Deconstructor):
    name = u"type"

    def deconstruct(self, obj):
        return None, {u"name" : STR(obj.__name__),
                      u"module" : STR(obj.__module__)}

    def construct(self, args, kwargs):
        class_name, module_name = kwargs["name"], kwargs["module"]
        mod = importlib.import_module(module_name) # package?
        return getattr(mod, class_name)
