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
import itertools
import nuke
import sgtk
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


NUKESTUDIO_PROJECTS_ITEM_TYPE_SETTINGS = {
    "nukestudio.project": {
        "publish_type": "NukeStudio Project",
        "publish_name_template": None,
        "publish_path_template": None
    }
}

class NukeStudioPublishProjectsPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """
    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish NukeStudio Project(S)"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        desc = super(NukeStudioPublishProjectsPlugin, self).description

        return desc + "<br><br>" + """
        After publishing, if a version number is detected in the file, the file
        will automatically be saved to the next incremental version number.
        For example, <code>filename.v001.ext</code> will be published and copied
        to <code>filename.v002.ext</code>

        If the next incremental version of the file already exists on disk, the
        validation step will produce a warning, and a button will be provided in
        the logging output which will allow saving the session to the next
        available version number prior to publishing.

        <br><br><i>NOTE: any amount of version number padding is supported.</i>
        """

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        schema = super(NukeStudioPublishProjectsPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"] = ["nukestudio.project"]
        schema["Item Type Settings"]["default_value"] = NUKESTUDIO_PROJECTS_ITEM_TYPE_SETTINGS
        return schema


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """
        publisher = self.parent

        # if the file has a version number in it, see if the next version exists
        next_version_path = publisher.util.get_next_version_path(item.properties.path)
        if next_version_path and os.path.exists(next_version_path):

            # determine the next available version_number. just keep asking for
            # the next one until we get one that doesn't exist.
            while os.path.exists(next_version_path):
                next_version_path = publisher.util.get_next_version_path(
                    next_version_path)

            # now extract the version number of the next available to display
            # to the user
            version = publisher.util.get_version_number(next_version_path)

            self.logger.error(
                "The next version of this file already exists on disk.",
                extra={
                    "action_button": {
                        "label": "Save to v%s" % (version,),
                        "tooltip": "Save to the next available version number, "
                                   "v%s" % (version,),
                        "callback": lambda: _save_session(next_version_path, item.properties.project)
                    }
                }
            )
            return False

        return super(NukeStudioPublishProjectsPlugin, self).validate(task_settings, item)


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # ensure the project is saved
        _save_session(sgtk.util.ShotgunPath.normalize(item.properties.path, item.properties.project))

        super(NukeStudioPublishProjectsPlugin, self).publish(task_settings, item)


    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        super(NukeStudioPublishProjectsPlugin, self).finalize(task_settings, item)

        # version up the script file if the publish went through successfully.
        if item.properties.get("sg_publish_data_list"):
            # insert the next version path into the properties
            item.properties.next_version_path = self._save_to_next_version(item.properties.path,
                                                                           _save_session,
                                                                           item.properties.project)


def _save_session(path, project):
    """
    Save the current session to the supplied path.
    :param path: str path to save the file
    :param project: Nuke Studio Project obj
    :return: None
    """

    # Nuke Studio won't ensure that the folder is created when saving, so we must make sure it exists
    ensure_folder_exists(os.path.dirname(path))
    project.saveAs(path)
