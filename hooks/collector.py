# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class BaseCollectorPlugin(HookBaseClass):
    """
    Base Collector Plugin class.
    """

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

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
        return {
            "Item Types": {
                "type": "dict",
                "values": {
                    "type": "dict"
                },
                "default_value": {},
                "description": (
                    "Dictionary of item types that the collector will attempt to "
                    "match and create instances of."
                )
            }
        }


    def process_current_session(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        raise NotImplementedError


    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """
        raise NotImplementedError
