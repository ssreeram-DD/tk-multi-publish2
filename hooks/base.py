# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class BasePlugin(HookBaseClass):
    """
    Base Plugin class.
    """
    def __init__(self, parent):
        """
        Construction
        """
        # call base init
        super(BasePlugin, self).__init__(parent)

        # initialize settings
        self.__settings = None

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        raise NotImplementedError

    @property
    def settings(self):
        """
        Dictionary of Settings. The keys are strings, matching
        the keys returned in the settings property. The values are `Setting`
        instances.
        """
        return self.__settings

    @settings.setter
    def settings(self, settings):
        # setter for value
        self.__settings = settings
