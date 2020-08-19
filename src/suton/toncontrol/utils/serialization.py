from enum import Enum
from typing import List, Dict


class JsonAware(object):

    class DataContainer(object):
        pass

    @classmethod
    def get_class_code_name(cls) -> str:
        return cls.__qualname__

    @classmethod
    def create(cls, data: dict):
        instance = cls()
        for item, val in data.items():
            try:
                default_val = getattr(instance, item)
            except AttributeError:
                continue
            if isinstance(default_val, Enum):
                val = default_val.__class__(val)
            setattr(instance, item, val)
        return instance

    def to_json(self):
        result = {
            "__class": self.get_class_code_name()
        }
        for attr in dir(self):
            value = getattr(self, attr)
            if not attr.startswith("_") and not callable(value):
                if isinstance(value, JsonAware):
                    result[attr] = value.to_json()
                elif isinstance(value, list):
                    result[attr] = []
                    for item in value:
                        if isinstance(item, JsonAware):
                            item = item.to_json()
                        result[attr].append(item)
                elif isinstance(value, Enum):
                    result[attr] = str(value)
                else:
                    result[attr] = value
        return result

    @staticmethod
    def from_json(data: dict, classes: List['JsonAware'] = None):
        class_map = {}
        for clazz in classes:
            class_map[clazz.get_class_code_name()] = clazz
        return JsonAware._from_json(data, class_map)

    @staticmethod
    def _from_json(data: dict, class_map: dict):
        data_container = dict()
        for item, value in data.items():
            if isinstance(value, dict) and value.get("__class"):
                data_container[item] = JsonAware._from_json(value, class_map)
            elif isinstance(value, list):
                data_container[item] = []
                for list_val in value:
                    if isinstance(list_val, dict) and list_val.get("__class"):
                        list_val = JsonAware._from_json(list_val, class_map)
                    data_container[item].append(list_val)
            elif item != "__class":
                data_container[item] = value
        _class_path = data.get("__class")
        _clazz = class_map.get(_class_path)
        if not _clazz:
            raise Exception("Class not present in class_map: {}".format(_class_path))
        if not issubclass(_clazz, JsonAware):
            raise Exception("Only JsonAware classes allowed in class map specs, got: {}".format(_clazz))
        return _clazz.create(data_container)
