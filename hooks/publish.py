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
import traceback
import pprint
import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


class BasePublishPlugin(HookBaseClass):
    """
    Base Publish Plugin class.
    """
    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        raise NotImplementedError

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        raise NotImplementedError

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        raise NotImplementedError

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
        return {
            "Item Type Filters": {
                "type": "list",
                "values": {
                    "type": "str",
                    "description": "A string pattern to match an item type against."
                },
                "default_value": [],
                "description": "A list of item types that this plugin is interested in."
            },
            "Item Type Settings": {
                "type": "dict",
                "values": {
                    "type": "dict"
                },
                "default_value": {},
                "description": (
                    "A dict of plugin settings keyed by item type. Each entry in the dict "
                    "is itself a dict in which each item is the plugin attribute name and value."
                ),
            }
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return self.settings["Item Type Filters"].value

    def init_task_settings(self, task_settings, item):
        """
        Method called by the publisher to determine the initial settings for the
        instantiated task.

        :param task_settings: Instance of the plugin settings specific for this item
        :param item: Item to process
        :returns: dictionary of settings for this item's task
        """
        # Return the item-type specific settings
        if item.type not in task_settings["Item Type Settings"].value:
            msg = "Key: %s\n%s" % (item.type, pprint.pformat(task_settings["Item Type Settings"].value))
            self.logger.warning(
                "'Item Type Settings' are missing for item type: '%s'" % item.type,
                extra={
                    "action_show_more_info": {
                        "label": "Show Info",
                        "tooltip": "Show more info",
                        "text": msg
                    }
                }
            )
            return None
        return task_settings["Item Type Settings"].value.get(item.type)

    def accept(self, task_settings, item):
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
        accept_data = {}

        # Only accept this item if we have its task settings dict
        if not task_settings:
            msg = "Unable to find task_settings for plugin: %s" % self.name
            accept_data["extra_info"] = {
                "action_show_more_info": {
                    "label": "Show Info",
                    "tooltip": "Show more info",
                    "text": msg
                }
            }
            accept_data["accepted"] = False
        else:
            accept_data["accepted"] = True

        return accept_data

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """
        raise NotImplementedError

    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        raise NotImplementedError

    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        raise NotImplementedError

    ############################################################################
    # protected methods

    def _copy_files(self, dest_path, item):
        """
        This method handles copying an item's path(s) to a designated location.

        If the item has "sequence_paths" set, it will attempt to copy all paths
        assuming they meet the required criteria.
        """

        publisher = self.parent

        # ---- get a list of files to be copied
        if item.properties["is_sequence"]:
            work_files = item.properties.get("sequence_paths", [])
        else:
            work_files = [item.properties["path"]]

        # ---- copy the work files to the publish location
        processed_files = []
        for work_file in work_files:

            if item.properties["is_sequence"]:
                frame_num = publisher.util.get_frame_number(work_file)
                dest_file = publisher.util.get_path_for_frame(dest_path, frame_num)
            else:
                dest_file = dest_path

            # If the file paths are the same, skip...
            if work_file == dest_file:
                continue

            # copy the file
            try:
                dest_folder = os.path.dirname(dest_file)
                ensure_folder_exists(dest_folder)
                copy_file(work_file, dest_file)
            except Exception as e:
                raise Exception(
                    "Failed to copy work file from '%s' to '%s'.\n%s" %
                    (work_file, dest_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to '%s'." % (work_file, dest_file)
            )
            processed_files.append(dest_file)

        return processed_files


    def _get_next_version_info(self, path, item, task_settings):
        """
        Return the next version of the supplied path.

        If templates are configured, use template logic. Otherwise, fall back to
        the zero configuration, path_info hook logic.

        :param str path: A path with a version number.
        :param item: The current item being published

        :return: A tuple of the form::

            # the first item is the supplied path with the version bumped by 1
            # the second item is the new version number
            (next_version_path, version)
        """

        if not path:
            self.logger.debug("Path is None. Can not determine version info.")
            return None, None

        publisher = self.parent

        next_version_path = publisher.util.get_next_version_path(path)
        cur_version = publisher.util.get_version_number(path)
        if cur_version:
            version = cur_version + 1
        else:
            version = None

        return next_version_path, version


    def _save_to_next_version(self, path, item, save_callback):
        """
        Save the supplied path to the next version on disk.

        :param path: The current path with a version number
        :param item: The current item being published
        :param save_callback: A callback to use to save the file

        Relies on the _get_next_version_info() method to retrieve the next
        available version on disk. If a version can not be detected in the path,
        the method does nothing.

        If the next version path already exists, logs a warning and does
        nothing.

        This method is typically used by subclasses that bump the current
        working/session file after publishing.
        """

        (next_version_path, version) = self._get_next_version_info(path, item)

        if version is None:
            self.logger.debug(
                "No version number detected in the publish path. "
                "Skipping the bump file version step."
            )
            return None

        self.logger.info("Incrementing file version number...")

        # nothing to do if the next version path can't be determined or if it
        # already exists.
        if not next_version_path:
            self.logger.warning("Could not determine the next version path.")
            return None
        elif os.path.exists(next_version_path):
            self.logger.warning(
                "The next version of the path already exists",
                extra={
                    "action_show_folder": {
                        "path": next_version_path
                    }
                }
            )
            return None

        # save the file to the new path
        save_callback(next_version_path)
        self.logger.info("File saved as: %s" % (next_version_path,))

        return next_version_path
