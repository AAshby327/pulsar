
import pulsar_console as import_mod

var = 0

_NULL_VAL = 0

def func(a: int):
    print(a)

class klass:

    class_var = 0

    def __init__(self, a: int):
        self.a = a

def get_members(obj) -> list[str]:

    members = []

    obj_dict = getattr(obj, '__dict__', dict())
    obj_slots = getattr(obj, '__slots__', tuple())

    entries = set(obj_dict)
    entries.update(obj_slots)

    obj_type = type(obj)

    for attr in dir(obj):

        val = getattr(obj, attr)
        is_callable = callable(val)

        if attr not in entries:

            # Skip class vars
            if getattr(obj_type, attr, _NULL_VAL) is val:
                continue

            # Skip class methods
            if is_callable and getattr(val, '__self__', obj) is not obj:
                continue

        members.append(attr)

    return members