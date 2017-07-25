from .. import Deconstructor


class WeakrefDeconstructor(Deconstructor):

    def deconstruct(self, obj):
        obj_dict = {u"object" : obj()}
        if obj.__callback__:
            obj_dict[u"callback"] = obj.__callback__
        return None, obj_dict

    def construct(self, args, kwargs):
        return self.cls(object=kwargs[u"object"],
                        callback=kwargs.get(u"callback"))
