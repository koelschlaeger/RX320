"""Helpers for reading saved settings (QSettings)."""


def read_setting(settings, key, value_type, default=None):
    """The saved value of key as value_type. Missing keys and unconvertible
    values (e.g. a hand-edited file) both give the default instead of
    stopping the app from starting."""
    if not settings.contains(key):
        return default
    try:
        return settings.value(key, type=value_type)
    except TypeError:
        return default
