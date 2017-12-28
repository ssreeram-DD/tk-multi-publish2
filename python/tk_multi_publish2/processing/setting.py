# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import copy
import sgtk

from ..util import Threaded

logger = sgtk.platform.get_logger(__name__)


class Setting(object):
    """
    A setting for a plugin or item
    """

    def __init__(self, setting_name, data_type, default_value, description=None):
        """
        :param setting_name: The name of the setting
        :param data_type: The data type of the setting
        :param default_value: The setting's default value
        :param description: Description of the setting
        """
        self._name = setting_name
        self._type = data_type
        self._default_value = default_value
        self._value = default_value
        self._description = description or ""

    @property
    def name(self):
        """
        The setting name
        """
        return self._name

    @property
    def value(self):
        """
        The current value of the setting
        """
        return self._value

    @value.setter
    def value(self, value):
        # setter for value
        self._value = value

    @property
    def string_value(self):
        """
        The setting value, as a string
        """
        return str(self._value)

    @property
    def description(self):
        """
        The description of the setting
        """
        return self._description

    @property
    def default_value(self):
        """
        The default value of the setting.
        """
        return self._default_value

    @property
    def type(self):
        """
        The data type of the setting.
        """
        return self._type


class SettingsCache(Threaded):
    """
    Cache of plugin settings per context.
    """
    def __init__(self):
        """
        Constructor.
        """
        Threaded.__init__(self)
        self._cache = dict()

    @Threaded.exclusive
    def get(self, plugin, context):
        """
        Retrieve the cached settings for a given context.

        :param context: The context for which we desire settings.

        :returns: The settings dictionary or None
        """
        return self._cache.get((plugin, repr(context)))

    @Threaded.exclusive
    def add(self, plugin, context, settings):
        """
        Cache settings for a given context.

        :param context: Context for which these settings need to be cached.
        :param settings: Settings to cache.
        """
        self._cache[(plugin, repr(context))] = copy.deepcopy(settings)

settings_cache = SettingsCache()
