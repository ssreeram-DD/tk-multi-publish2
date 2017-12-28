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
import maya.cmds as cmds
import maya.mel as mel
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaCreateVersionPlugin(HookBaseClass):
    """
    Inherits from CreateVersionPlugin
    """
    ############################################################################
    # protected methods

    def _get_colorspace(self, task_settings, item):
        """
        Get the colorspace for the specified maya session

        :returns:       The string representing the colorspace for the maya session
        """
        return cmds.colorManagementPrefs(q=True, renderingSpaceName=True)


    def _get_frame_range(self, task_settings, item):
        """
        Get the animation range from the current scene.
        """
        return (int(cmds.playbackOptions(q=True, min=True)),
                int(cmds.playbackOptions(q=True, max=True)))
