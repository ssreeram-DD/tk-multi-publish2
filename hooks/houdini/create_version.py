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
import hou
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HoudiniCreateVersionPlugin(HookBaseClass):
    """
    Inherits from CreateVersionPlugin
    """
    ############################################################################
    # protected methods

    def _get_colorspace(self, task_settings, item):
        """
        Get the colorspace for the specified nuke node

        :param node:    The houdini node to find the colorspace for
        :returns:       The string representing the colorspace for the node
        """
        node = item.properties.node
        if node:
            return node.evalParm("vm_colorspace")
        else:
            return "default"


    def _get_frame_range(self, task_settings, item):
        """
        Get the nuke session frame range
        """
        return map(lambda x: int(x), hou.playbar.playbackRange())
