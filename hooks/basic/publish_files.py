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
import glob
import pprint
import traceback

import sgtk
from sgtk import TankError

HookBaseClass = sgtk.get_hook_baseclass()


DEFAULT_ITEM_TYPE_SETTINGS = {
    "file.alembic": {
        "publish_type": "Alembic Cache",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.3dsmax": {
        "publish_type": "3dsmax Scene",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.nukestudio": {
        "publish_type": "NukeStudio Project",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.houdini": {
        "publish_type": "Houdini Scene",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.maya": {
        "publish_type": "Maya Scene",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.motionbuilder": {
        "publish_type": "Motion Builder FBX",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.nuke": {
        "publish_type": "Nuke Script",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.photoshop": {
        "publish_type": "Photoshop Image",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.render.sequence": {
        "publish_type": "Rendered Image",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.texture": {
        "publish_type": "Texture Image",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.image": {
        "publish_type": "Image",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
    "file.video": {
        "publish_type": "Movie",
        "publish_name_template": None,
        "work_path_template": None,
        "publish_path_template": None
    },
}

class PublishFilesPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun.

    This plugin is typically configured to act upon files that are dragged and
    dropped into the publisher UI. It can also be used as a base class for
    other file-based publish plugins as it contains standard operations for
    validating and registering publishes with Shotgun.

    Once attached to a publish item, the plugin will key off of properties that
    are set on the item. These properties can be set via the collector or
    by subclasses prior to calling methods on this class.

    The only property that is required for the plugin to operate is the ``path``
    property. All of the properties and settings understood by the plugin are
    documented below:

        Item properties
        -------------

        path - The path to the file to be published.

        sequence_paths - If set, implies the "path" property represents a
            sequence of files (typically using a frame identifier such as %04d).
            This property should be a list of files on disk matching the "path".
            If a work template is provided, and corresponds to the listed
            frames, fields will be extracted and applied to the publish template
            (if set) and copied to that publish location.

        is_sequence - A boolean defining whether or not this item is a sequence of files.

        publish_dependencies - A list of files to include as dependencies when
            registering the publish. If the item's parent has been published,
            it's path will be appended to this list.

        Task settings
        -------------------

        publish_type - If set in the plugin settings dictionary, will be
            supplied to SG as the publish type when registering "path" as a new
            publish. This is required.

        publish_name_template - If set in the plugin settings dictionary, will be
            supplied to SG as the publish name when registering the new publish.
            If not available, will be determined by the "work_path_template"
            property if available, falling back to the ``path_info`` hook
            logic.

        work_path_template - If set in the plugin settings dictionary, is used
            to validate "path" and extract fields for further processing and
            contextual discovery. For example, if configured and a version key
            can be extracted, it will be used as the publish version to be
            registered in Shotgun.

        publish_path_template - If set in the plugin settings dictionary, used to
            determine where "path" should be copied prior to publishing. If
            not specified, "path" will be published in place.

    This plugin will also set the following properties on the item which may be 
    useful for child items.

        publish_type - Shotgun PublishedFile instance type.

        publish_name - Shotgun PublishedFile instance name.

        publish_version - Shotgun PublishedFile instance version.

        publish_path - The location on disk the publish is copied to.

        sg_publish_data - The dictionary of publish information returned from
            the tk-core register_publish method.

    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        # look for icon one level up from this hook's folder in "icons" folder
        return self.parent.expand_path("{self}/hooks/icons/publish.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish File(s)"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        Publishes the file to Shotgun. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the file's current
        path on disk. Other users will be able to access the published file via
        the <b><a href='%s'>Loader</a></b> so long as they have access to
        the file's location on disk.

        <h3>File versioning</h3>
        The <code>version</code> field of the resulting <b>Publish</b> in
        Shotgun will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        <br><br><i>NOTE: any amount of version number padding is supported.</i>

        <h3>Overwriting an existing publish</h3>
        A file can be published multiple times however only the most recent
        publish will be available to other users. Warnings will be provided
        during validation if there are previous publishes.
        """ % (loader_url,)

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
        schema = super(PublishFilesPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"] = ["file.*"]
        schema["Item Type Settings"]["default_value"] = DEFAULT_ITEM_TYPE_SETTINGS
        schema["Item Type Settings"]["values"]["items"] = {
            "publish_type": {
                "type": "shotgun_publish_type",
                "description": "",
            },
            "publish_name_template": {
                "type": "template",
                "description": "",
                "fields": ["context", "version", "[output]", "[name]", "*"],
                "allows_empty": True,
            },
            "work_path_template": {
                "type": "template",
                "description": "",
                "fields": ["context", "*"],
                "allows_empty": True,
            },
            "publish_path_template": {
                "type": "template",
                "description": "",
                "fields": ["context", "*"],
                "allows_empty": True,
            },
        }
        return schema


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

        # Run the parent acceptance method
        accept_data = super(PublishFilesPlugin, self).accept(task_settings, item)
        if not accept_data.get("accepted"):
            return accept_data

        path = item.properties.get("path")
        if not path:
            accept_data["accepted"] = False
            return accept_data

        # return the accepted data
        return accept_data


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent

        # ---- ensure that work file(s) exist on disk to be published

        if item.properties["is_sequence"]:
            if not item.properties["sequence_paths"]:
                self.logger.warn("File sequence does not exist: %s" % item.properties["path"])
                return False
        else:
            if not os.path.exists(item.properties["path"]):
                self.logger.warn("File does not exist: %s" % item.properties["path"])
                return False

        # ---- validate the settings required to publish

        attr_list = ("publish_type", "publish_path", "publish_name", "publish_version")
        for attr in attr_list:
            try:
                method = getattr(self, "_get_%s" % attr)
                item.properties[attr] = method(item, task_settings)
            except Exception:
                self.logger.error(
                    "Unable to determine '%s' for item: %s" % (attr, item.name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )
                return False

        # ---- check for conflicting publishes of this path with a status

        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.
        publishes = publisher.util.get_conflicting_publishes(
            item.context,
            item.properties["publish_path"],
            item.properties["publish_name"],
            filters=["sg_status_list", "is_not", None]
        )

        if publishes:
            conflict_info = (
                "If you continue, these conflicting publishes will no longer "
                "be available to other users via the loader:<br>"
                "<pre>%s</pre>" % (pprint.pformat(publishes),)
            )
            self.logger.warn(
                "Found %s conflicting publishes in Shotgun" %
                    (len(publishes),),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show the conflicting publishes in Shotgun",
                        "text": conflict_info
                    }
                }
            )

        # ---- ensure the published file(s) don't already exist on disk

        conflict_info = None
        if item.properties["is_sequence"]:
            seq_pattern = publisher.util.get_path_for_frame(item.properties["publish_path"], "*")
            seq_files = [f for f in glob.iglob(seq_pattern) if os.path.isfile(f)]

            if seq_files:
                conflict_info = (
                    "The following files already exist!<br>"
                    "<pre>%s</pre>" % (pprint.pformat(seq_files),)
                )
        else:
            if os.path.exists(item.properties["publish_path"]):
                conflict_info = (
                    "The following file already exists!<br>"
                    "<pre>%s</pre>" % (item.properties["publish_path"],)
                )

        if conflict_info:
            self.logger.error(
                "Version '%s' of this file already exists on disk." %
                    (item.properties["publish_version"],),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show the conflicting published files",
                        "text": conflict_info
                    }
                }
            )
            return False

        self.logger.info("A Publish will be created in Shotgun and linked to: %s" %
                (item.properties["publish_path"],))

        return True


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # Get item properties populated by validate method
        publish_name     = item.properties["publish_name"]
        publish_path     = item.properties["publish_path"]
        publish_type     = item.properties["publish_type"]
        publish_version  = item.properties["publish_version"]

        # handle copying of work to publish
        self._copy_files(publish_path, item)

        # if the parent item has a publish path, include it in the list of
        # dependencies
        dependency_paths = item.properties.get("publish_dependencies", [])
        if "sg_publish_path" in item.parent.properties:
            dependency_paths.append(item.parent.properties["sg_publish_path"])

        # arguments for publish registration
        self.logger.info("Registering publish...")
        publish_data= {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": item.get_thumbnail_as_path() or "",
            "published_file_type": publish_type,
            "dependency_paths": dependency_paths
        }

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),)
                }
            }
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(
            **publish_data)
        self.logger.info("Publish registered!")


    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # get the data for the publish that was just created in SG
        publish_data = item.properties["sg_publish_data"]

        # ensure conflicting publishes have their status cleared
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data)

        self.logger.info(
            "Cleared the status of all previous, conflicting publishes")

        path = item.properties["path"]
        self.logger.info(
            "Publish created for file: %s" % (path,),
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Publish",
                    "tooltip": "Open the Publish in Shotgun.",
                    "entity": publish_data
                }
            }
        )


    ############################################################################
    # protected methods

    def _get_publish_type(self, item, task_settings):
        """
        Get a publish type for the supplied item.

        :param item: The item to determine the publish type for

        :return: A publish type or None if one could not be found.
        """
        publish_type = task_settings.get("publish_type")
        if not publish_type:
            raise TankError("publish_type not set for item: %s" % item.name)

        return publish_type


    def _get_publish_path(self, item, task_settings):
        """
        Get a publish path for the supplied item.

        :param item: The item to determine the publish type for

        :return: A string representing the output path to supply when
            registering a publish for the supplied item

        Extracts the publish path via the configured work and publish templates
        if possible.
        """

        publisher = self.parent

        # Use the work_file_path if defined
        path = item.properties.get("work_file_path")
        if not path:
            path = item.properties.get("path")

        work_path_template = task_settings.get("work_path_template")
        publish_path_template = task_settings.get("publish_path_template")
        publish_path = None

        fields = {}
        # If a template is defined, get the publish path from it
        if publish_path_template:

            pub_tmpl = publisher.get_template_by_name(publish_path_template)
            if not pub_tmpl:
                # this template was not found in the template config!
                raise TankError("The Template '%s' does not exist!" % publish_path_template)

            # First get the fields from the context
            try:
                fields.update(item.context.as_template_fields(pub_tmpl, validate=True))
            except TankError, e:
                self.logger.debug(
                    "Unable to get context fields for publish_path_template.")

            # Next if there is a work_path_template, use it to get fields from the input path
            if work_path_template:

                work_tmpl = publisher.get_template_by_name(work_path_template)
                if not work_tmpl:
                    # this template was not found in the template config!
                    raise TankError("The Template '%s' does not exist!" % work_path_template)

                if work_tmpl.validate(path):
                    self.logger.debug(
                        "Work file template configured and matches file.")
                    fields.update(work_tmpl.get_fields(path))

            missing_keys = pub_tmpl.missing_keys(fields, True)
            if missing_keys:
                raise TankError(
                    "Cannot resolve publish_path_template (%s). Missing keys: %s" %
                            (publish_path_template, pprint.pformat(missing_keys))
                )

            # Apply fields to publish_path_template to get publish path
            publish_path = pub_tmpl.apply_fields(fields)
            self.logger.debug(
                "Used publish_path_template to determine the publish path: %s" %
                (publish_path,)
            )

        # Otherwise fallback to publishing in place
        else:
            publish_path = path
            self.logger.debug(
                "No publish_path_template defined. Publishing in place.")

        return publish_path


    def _get_publish_version(self, item, task_settings):
        """
        Get the publish version for the supplied item.

        :param item: The item to determine the publish version for

        Extracts the publish version via the configured work template if
        possible. Will fall back to using the path info hook.
        """

        publisher = self.parent

        # Use the work_file_path if defined
        path = item.properties.get("work_file_path")
        if not path:
            path = item.properties.get("path")

        work_path_template = task_settings.get("work_path_template")
        work_fields = None
        publish_version = None

        fields = {}
        # First attempt to get it from the work_path_template
        if work_path_template:

            work_tmpl = publisher.get_template_by_name(work_path_template)
            if not work_tmpl:
                # this template was not found in the template config!
                raise TankError("The Template '%s' does not exist!" % work_path_template)

            # First get the fields from the context
            try:
                fields.update(item.context.as_template_fields(work_tmpl, validate=True))
            except TankError, e:
                self.logger.debug(
                    "Unable to get context fields from work_path_template.")

            # Then attempt to get the fields from the path
            if work_tmpl.validate(path):
                self.logger.debug(
                    "Work file template configured and matches file.")
                fields.update(work_tmpl.get_fields(path))

            # if version number is one of the fields, use it to populate the
            # publish information
            if "version" not in fields:
                raise TankError(
                    "Unable to get version field from work_path_template (%s)"
                    % work_path_template)

            publish_version = fields.get("version")
            self.logger.debug(
                "Retrieved version number via work file template.")

        # Otherwise fallback on file path parsing
        else:
            self.logger.debug("Using path info hook to determine publish info.")
            publish_version = publisher.util.get_version_number(path) or 1

        return publish_version


    def _get_publish_name(self, item, task_settings):
        """
        Get the publish name for the supplied item.

        :param item: The item to determine the publish version for

        Uses the path info hook to retrieve the publish name.
        """

        publisher = self.parent

        # Use the work_file_path if defined
        path = item.properties.get("work_file_path")
        if not path:
            path = item.properties.get("path")

        publish_name_template = task_settings.get("publish_name_template")
        work_path_template = task_settings.get("work_path_template")
        publish_name = None

        fields = {}
        # First attempt to get fields from the work_path_template if defined
        if work_path_template:

            work_tmpl = publisher.get_template_by_name(work_path_template)
            if not work_tmpl:
                # this template was not found in the template config!
                raise TankError("The Template '%s' does not exist!" % work_path_template)

            if work_tmpl.validate(path):
                # First get the fields from the context
                try:
                    fields.update(item.context.as_template_fields(work_tmpl, validate=True))
                    self.logger.debug(
                        "Getting context fields from work_path_template.")
                except TankError, e:
                    self.logger.debug(
                        "Unable to get context fields for work_path_template.")

                fields.update(work_tmpl.get_fields(path))
                self.logger.debug(
                    "Work file template configured and matches file.")

        # Next check if we have a publish_name_template defined and attempt to
        # get the publish name from that
        if publish_name_template:

            pub_tmpl = publisher.get_template_by_name(publish_name_template)
            if not pub_tmpl:
                # this template was not found in the template config!
                raise TankError("The Template '%s' does not exist!" % publish_name_template)

            # First get the fields from the context
            try:
                fields.update(item.context.as_template_fields(pub_tmpl, validate=True))
            except TankError, e:
                self.logger.debug(
                    "Unable to get context fields for publish_name_template.")

            missing_keys = pub_tmpl.missing_keys(fields, True)
            if missing_keys:
                raise TankError(
                    "Cannot resolve publish_name_template (%s). Missing keys: %s" %
                            (publish_name_template, pprint.pformat(missing_keys))
                )

            publish_name = pub_tmpl.apply_fields(fields)
            self.logger.debug(
                "Retrieved publish_name via publish_name_template.")

        # Otherwise fallback on file path parsing
        else:

            # Try getting the file path from the work_template if defined
            if work_tmpl:
                missing_keys = work_tmpl.missing_keys(fields, True)
                if missing_keys:
                    self.logger.warning(
                        "Cannot resolve work_path_template (%s). Missing keys: %s" %
                        (work_path_template, pprint.pformat(missing_keys))
                    )
                    name_path = None
                else:
                    name_path = work_tmpl.apply_fields(fields)
                    self.logger.debug(
                        "Retrieved publish_name via work_path_template.")

            # Otherwise fallback to the input path name
            if not name_path:
                name_path = path
                self.logger_debug(
                    "Retrieved publish_name via source file path.")

            # Use built-in method for determining publish_name
            publish_name = publisher.util.get_publish_name(name_path)

        return publish_name
