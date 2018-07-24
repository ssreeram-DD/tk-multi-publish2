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
import itertools

HookBaseClass = sgtk.get_hook_baseclass()


NUKE_SESSION_ITEM_TYPE_SETTINGS = {
    "nuke.session": {
        "publish_type": "Nuke Script",
        "publish_name_template": None,
        "publish_path_template": None
    }
}

# A list of input node types to check as dependencies
_NUKE_INPUTS = ("Read", "ReadGeo2", "Camera2")

class NukePublishSessionPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """
    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Nuke Session"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        desc = super(NukePublishSessionPlugin, self).description

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
        schema = super(NukePublishSessionPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"].append("nuke.session")
        schema["Item Type Settings"]["default_value"].update(NUKE_SESSION_ITEM_TYPE_SETTINGS)
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

        if item.type == 'nuke.session':

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
                            "callback": lambda: _save_session(next_version_path)
                        }
                    }
                )
                return False

        return super(NukePublishSessionPlugin, self).validate(task_settings, item)


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # ensure the session is saved
        if item.type == 'nuke.session':
            _save_session(sgtk.util.ShotgunPath.normalize(item.properties.path))

            # Store any file dependencies
            item.properties.publish_dependency_paths = self._get_dependency_paths()

        super(NukePublishSessionPlugin, self).publish(task_settings, item)


    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        super(NukePublishSessionPlugin, self).finalize(task_settings, item)

        # version up the script file if the publish went through successfully.
        if item.type == 'nuke.session' and item.properties.get("sg_publish_data_list"):
            # insert the next version path into the properties
            item.properties.next_version_path = self._save_to_next_version(item.properties.path, _save_session)


    def _get_dependency_paths(self, node=None):
        """
        Find all dependency paths for the current node. If no node specified,
        will return all dependency paths for the nuke script.

        :param node: Optional node to process
        :return: List of upstream dependency paths
        """
        publisher = self.parent

        if node:
            allnodes = nuke.allNodes()
            visited = {nodes: 0 for nodes in allnodes}
            # Collect all upstream nodes to specified node
            dep_nodes = []
            input_nodes = _collect_dep_nodes(node, visited, dep_nodes)
        else:
            # Collect all nodes in this nuke script
            # dep_nodes = nuke.allNodes()
            input_node_lists = [nuke.allNodes(node) for node in _NUKE_INPUTS]
            input_nodes = list(itertools.chain(*(node for node in input_node_lists)))

        # Only process nodes that match one of the specified input types
        # input_nodes = [node for node in dep_nodes if node.Class() in _NUKE_INPUTS]

        # figure out all the inputs to the node and pass them as dependency
        # candidates
        dependency_paths = []
        for dep_node in input_nodes:
            if dep_node['disable'].value() == 1:
                continue
            file_path = dep_node.knob('file').evaluate()
            if not file_path:
                continue

            file_path = sgtk.util.ShotgunPath.normalize(file_path)

            # Check if the input path contains a frame number
            seq_path = publisher.util.get_frame_sequence_path(file_path)
            if seq_path:
                # If so, then use the path with the frame number replaced with the frame spec
                file_path = seq_path

            dependency_paths.append(file_path)

        return dependency_paths


def _collect_dep_nodes(node, visited, dep_nodes):
    """
    For each specified node, traverse the node graph and get any associated upstream nodes.

    :param nodes: List of nodes to process
    :return: List of upstream dependency nodes
    """
    # dependency_list = list(itertools.chain(*(node.dependencies() for node in nodes)))
    # if dependency_list:
    #     depends = _collect_dep_nodes(dependency_list)
    #     for item in depends:
    #         nodes.append(item)
    #
    # # Remove duplicates
    # return list(set(nodes))
    if visited[node] == 0:
        if node.Class() in _NUKE_INPUTS and (node['disable'].value() == 0):
            dep_nodes.append(node)
        # set visited to 1 for the node so as not to revisit
        visited[node] = 1
        dep = node.dependencies()
        if dep:
            for item in dep:
                _collect_dep_nodes(item, visited, dep_nodes)
    return dep_nodes


def _save_session(path):
    """
    Save the current session to the supplied path.
    """
    nuke.scriptSaveAs(path, True)
