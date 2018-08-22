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
import re
import mari
import sgtk
from sgtk import TankError
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


MARI_SESSION_ITEM_TYPE_SETTINGS = {
    "mari.session": {
        "publish_type": "Mari Session",
        "publish_name_template": None,
        "publish_path_template": None
    }
}

class MariPublishSessionPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """
    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Mari Session"

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
        schema = super(MariPublishSessionPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"] = ["mari.session"]
        schema["Item Type Settings"]["default_value"] = MARI_SESSION_ITEM_TYPE_SETTINGS
        return schema


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        self.logger.info("Saving the current project...")
        mari.projects.current().save()

        # Store any publish dependencies
        item.properties.publish_dependency_ids = self._get_dependency_ids()

        return super(MariPublishSessionPlugin, self).publish(task_settings, item)


    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        super(MariPublishSessionPlugin, self).finalize(task_settings, item)

        # version up the session if the publish went through successfully.
        if item.properties.get("sg_publish_data_list"):
            # save the new version number in the session metadata
            next_version = int(item.properties.publish_version) + 1

            self.logger.info("Versioning up session to v%03d" % next_version)
            self.parent.engine.set_project_version(item.properties.project, next_version)

            # Save the session
            mari.projects.current().save()


    def publish_files(self, task_settings, item, publish_path):
        """
        Overrides the inherited method to export out session items to the publish_path location.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :param publish_path: The output path to publish files to
        """
        return self._export_mari_session(task_settings, item, publish_path)


    def _export_mari_session(self, task_settings, item, publish_path):
        """
        Exports out an msf file to the specified directory
        """
        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(publish_path)

        try:
            # ensure the publish folder exists:
            ensure_folder_exists(path)

            # Export out an msf file
            mari.session.exportSession(path)

        except Exception as e:
            raise TankError("Failed to publish session item '%s': %s" % (item.name, str(e)))

        self.logger.info("Published session item '%s' to '%s'." % (item.name, path))
        return [path]


    def _get_dependency_ids(self):
        """
        Find additional dependencies for the session
        """
        publish_ids = []

        # Collect the geometry publish ids
        for geo_item in self.parent.engine.list_geometry():
            geo = geo_item.get("geo")
            if not geo:
                continue

            # Get the current geo version
            current_version = geo.currentVersion()

            # Get the version metadata
            version_metadata = self.parent.engine.get_shotgun_info(current_version)
            geo_version_publish_id = version_metadata.get("publish_id")
            if not geo_version_publish_id:
                continue

            publish_ids.append(geo_version_publish_id)

        return publish_ids
