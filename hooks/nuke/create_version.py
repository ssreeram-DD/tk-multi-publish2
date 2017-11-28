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
import pprint
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class NukeCreateVersionPlugin(HookBaseClass):
    """
    Inherits from CreateVersionPlugin
    """
    def __init__(self, parent):
        """
        Construction
        """
        # call base init
        super(NukeCreateVersionPlugin, self).__init__(parent)
        
        # cache the write node app
        self.__write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")


    def accept(self, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # Run the parent acceptance method
        accept_data = super(NukeCreateVersionPlugin, self).accept(item)
        if not accept_data.get("accepted"):
            return accept_data

        # If this is a WriteTank node, override task settings from the node
        node = item.properties.get("node")
        if node and node.Class() == "WriteTank":
            if not self.__write_node_app:
                self.logger.error("Unable to process item '%s' without "
                        "the tk-nuke_writenode app!" % item.name)
                accept_data["enabled"] = False
                accept_data["checked"] = False
                return accept_data

            accept_data["task_settings"] = dict(
                work_path_template    = self.__write_node_app.get_node_render_template(node).name,
                publish_path_template = self.__write_node_app.get_node_publish_template(node).name
            )

        # return the accepted info
        return accept_data


    ############################################################################
    # protected methods

    def _get_colorspace(self, task_settings, item):
        """
        Get the colorspace for the specified nuke node

        :param node:    The nuke node to find the colorspace for
        :returns:       The string representing the colorspace for the node
        """
        node = item.properties["node"]

        cs_knob = node.knob("colorspace")
        if not cs_knob:
            return
    
        cs = cs_knob.value()
        # handle default value where cs would be something like: 'default (linear)'
        if cs.startswith("default (") and cs.endswith(")"):
            cs = cs[9:-1]
        return cs


    def _get_frame_range(self, task_settings, item):
        """
        Get the nuke session frame range
        """
        return (int(nuke.root()["first_frame"].value()),
                int(nuke.root()["last_frame"].value()))
