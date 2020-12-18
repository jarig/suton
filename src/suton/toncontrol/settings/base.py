from toncommon.serialization.json import JsonAware


class BaseTonControlSettings(JsonAware):

    def __str__(self):
        result = ""
        for attr in dir(self):
            value = getattr(self, attr)
            if not attr.startswith("_") and not callable(value):
                str_val = str(value).splitlines()
                str_fmt_val = str_val[0]
                for s_val in str_val[1:]:
                    str_fmt_val = "{}\n  {}".format(str_fmt_val, s_val)
                result = "{}\n{}({}) = {}".format(result, attr, type(value), str_fmt_val)
        return result


