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
from sgtk import TankError

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
        return self._cache.get((plugin, context))

    @Threaded.exclusive
    def add(self, plugin, context, settings):
        """
        Cache settings for a given context.

        :param context: Context for which these settings need to be cached.
        :param settings: Settings to cache.
        """
        self._cache[(plugin, context)] = copy.deepcopy(settings)

settings_cache = SettingsCache()


def get_raw_plugin_settings(plugin, context):
    """
    Find settings for the plugin in the specified context

    :param plugin: Plugin to match the settings for.
    :param context: Context in which to look for settings.

    :returns: The plugin settings for the given context or None.
    """
    app = plugin._bundle

    if not context:
        raise TankError("No context specified.")

    env = sgtk.platform.engine.get_environment_from_context(app.sgtk, context)
    if not env:
        raise TankError("Cannot determine environment for context: %s" % context)

    # find settings for all instances of app in the environment picked for the given context:
    app_settings_list = sgtk.platform.find_app_settings(
        app.engine.name,
        app.name,
        app.sgtk,
        context,
        app.engine.instance_name
    )

    # No settings found, raise an error
    if not app_settings_list:
        raise TankError("Cannot find settings for %s in env: '%s' for context "
            "%s" % (app.name, env.name, context)
        )

    if len(app_settings_list) > 1:
        # There's more than one instance of that app for the engine instance, so we'll
        # need to deterministically pick one. We'll pick the one with the same
        # application instance name as the current app instance.
        for settings in app_settings:
            if settings.get("app_instance") == app.instance_name:
                app_settings = settings.get("settings")
                break
    else:
        app_settings = app_settings_list[0].get("settings")

    if not app_settings:
        raise TankError(
            "Search for %s settings in env '%s' for context %s yielded too "
            "many results (%s), none named '%s'" % (app.name, env.name, context,
            ", ".join([s.get("app_instance") for s in app_settings_list]),
            app.instance_name)
        )

    # Now get the plugin settings matching this plugin
    plugin_defs = app.get_setting_from(app_settings, "publish_plugins")
    for plugin_def in plugin_defs:
        if plugin_def["name"] == plugin.name:
            return plugin_def["settings"]

    raise TankError(
        "Definition for app '%s' in env '%s' is missing settings for plugin "
        "'%s' for context %s" % (app.instance_name, env.name, plugin.name, context)
    )
