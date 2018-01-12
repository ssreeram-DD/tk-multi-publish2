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
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# A look up of node types to parameters for finding outputs to publish
_NUKE_OUTPUTS = {
    "WriteTank": "file",
    "Write": "file",
    "WriteGeo": "file",
}


class NukeSessionCollector(HookBaseClass):
    """
    Collector that operates on the current nuke/nukestudio session. Should
    inherit from the basic collector hook.
    """
    def __init__(self, parent):
        """
        Construction
        """
        # call base init
        super(NukeSessionCollector, self).__init__(parent)

        # cache the write node and workfiles apps
        self.__write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        self.__workfiles_app = self.parent.engine.apps.get("tk-multi-workfiles2")


    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Nuke/NukeStudio and parents a
        subtree of items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent
        engine = publisher.engine

        if hasattr(engine, "studio_enabled") and engine.studio_enabled:
            # running nuke studio.
            self.collect_current_nukestudio_session(parent_item)

            # since we're in NS, any additional collected outputs will be
            # parented under the root item
            session_item = parent_item
        else:
            # running nuke. ensure additional collected outputs are parented
            # under the session
            session_item = self.collect_current_nuke_session(parent_item)

        self.collect_node_outputs(session_item)


    def collect_current_nuke_session(self, parent_item):
        """
        Analyzes the current session open in Nuke and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent

        # get the current path
        file_path = _session_path()
        if not file_path:
            # the session has not been saved before (no path determined).
            # provide a save button. the session will need to be saved before
            # validation will succeed.
            self.logger.warn(
                "The Nuke script has not been saved.",
                extra=self._get_save_as_action()
            )

        session_item = super(NukeSessionCollector, self)._add_file_item(
            parent_item,
            file_path
        )

        if session_item:
            session_item.name = "Current Nuke Session"

        return session_item


    def collect_current_nukestudio_session(self, parent_item):
        """
        Analyzes the current session open in NukeStudio and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # import here since the hooks are imported into nuke and nukestudio.
        # hiero module is only available in later versions of nuke
        import hiero.core

        # go ahead and build the path to the icon for use by any projects
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "nukestudio.png"
        )

        active_project = hiero.ui.activeSequence().project()

        for project in hiero.core.projects():

            # create the session item for the publish hierarchy
            session_item = parent_item.create_item(
                "file.nukestudio",
                "NukeStudio Project",
                project.name(),
                self
            )
            session_item.set_icon_from_path(icon_path)

            # add the project object to the properties so that the publish
            # plugins know which open project to associate with this item
            session_item.properties["project"] = project

            self.logger.info(
                "Collected Nuke Studio project: %s" % (project.name(),))

            # enable the active project and expand it. other projects are
            # collapsed and disabled.
            if active_project and active_project.guid() == project.guid():
                session_item.expanded = True
                session_item.checked = True
            elif active_project:
                # there is an active project, but this isn't it. collapse and
                # disable this item
                session_item.expanded = False
                session_item.checked = False


    def collect_node_outputs(self, parent_item):
        """
        Scan known output node types in the session and see if they reference
        files that have been written to disk.

        :param parent_item: The parent item for any write geo nodes collected
        """
        publisher = self.parent

        # iterate over all the known output types
        for node_type in _NUKE_OUTPUTS:

            # get all the instances of the node type
            all_nodes_of_type = [n for n in nuke.allNodes()
                if n.Class() == node_type]

            # iterate over each instance
            for node in all_nodes_of_type:

                self.logger.info(
                    "Processing %s node: %s" % (node_type, node.name()))

                if node_type == "WriteTank":

                    if not self.__write_node_app:
                        self.logger.error("Unable to process node '%s' without "
                                "the tk-nuke_writenode app!" % node.name())
                        continue

                    # Get the file path and sequence files from the node itself
                    file_path = self.__write_node_app.get_node_render_path(node)
                    thumbnail = self.__write_node_app.generate_node_thumbnail(node)

                else:
                    # evaluate the output path parameter which may include frame
                    # expressions/format
                    param_name = _NUKE_OUTPUTS[node_type]
                    file_path = node[param_name].evaluate()
                    thumbnail = None

                # Call the parent _collect_file method
                item = super(NukeSessionCollector, self)._collect_file(
                    parent_item,
                    file_path
                )

                # the item has been created. update the display name to include
                # the nuke node to make it clear to the user how it was
                # collected within the current session. also, prepend nukesession
                # to the item type so we can process it by the nuke-specific publish
                if item:
                    item.name = "%s (%s)" % (item.name, node.name())

                    # Store a reference to the originating node
                    item.properties["node"] = node

                    if thumbnail:
                        item.set_thumbnail_from_path(thumbnail)


    def _get_workfile_name_field(self, item):
        """
        """
        if item.type == "file.nuke":
            return item.properties["fields"].get("name")

        elif item.parent and not item.parent.is_root():
            return self._get_workfile_name_field(item.parent)

        return None


    def _resolve_item_fields(self, item):
        """
        Helper method used to get fields that might not normally be defined in the context.
        Intended to be overridden by DCC-specific subclasses.
        """
        # run the parent method first
        fields = super(NukeSessionCollector, self)._resolve_item_fields(item)

        # If this is a nuke session...
        if item.type == "file.nuke":
            if self.__workfiles_app:
                # Get work_path_template from the workfiles app for the item's context
                work_path_template = self.__workfiles_app.get_work_template(item.context)
                if work_path_template.validate(item.properties["path"]):
                    fields.update(work_path_template.get_fields(item.properties["path"]))

        # Else get the "name" field from the parent workfile
        else:
            workfile_name = self._get_workfile_name_field(item)
            if workfile_name:
                fields["name"] = workfile_name


        node = item.properties.get("node")
        if node:
            if node.Class() == "WriteTank":
                if self.__write_node_app:
                    # Get work_path_template from the write_node app and update fields
                    work_path_template = self.__write_node_app.get_node_render_template(node)
                    if work_path_template.validate(item.properties["path"]):
                        fields.update(work_path_template.get_fields(item.properties["path"]))
                else:
                    self.logger.error("Unable to process item '%s' without "
                            "the tk-nuke_writenode app!" % item.name)

            # Else just get height, width, and output from the node
            else:
                fields["width"] = node.width()
                fields["height"] = node.height()
                fields["output"] = node.name()

        return fields


    def _get_save_as_action(self):
        """
        Simple helper for returning a log action dict for saving the session
        """
        # default save callback
        callback = nuke.scriptSaveAs

        # if workfiles2 is configured, use that for file save
        if self.__workfiles_app:
            callback = self.__workfiles_app.show_file_save_dlg

        return {
            "action_button": {
                "label": "Save As...",
                "tooltip": "Save the current session",
                "callback": callback
            }
        }


def _session_path():
    """
    Return the path to the current session
    :return:
    """
    root_name = nuke.root().name()
    return None if root_name == "Root" else root_name

