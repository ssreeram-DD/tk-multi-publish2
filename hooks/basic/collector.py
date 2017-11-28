# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import glob
import pprint
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


# This is a dictionary of file type info that allows the basic collector to
# identify common production file types and associate them with a display name,
# item type, and config icon.
DEFAULT_ITEM_TYPES = {
    "file.alembic": {
        "extensions": ["abc"],
        "icon": "{self}/hooks/icons/alembic.png",
        "type_display": "Alembic Cache"
    },
    "file.3dsmax": {
        "extensions": ["max"],
        "icon": "{self}/hooks/icons/3dsmax.png",
        "type_display": "3dsmax Scene"
    },
    "file.nukestudio": {
        "extensions": ["hrox"],
        "icon": "{self}/hooks/icons/nukestudio.png",
        "type_display": "NukeStudio Project"
    },
    "file.houdini": {
        "extensions": ["hip", "hipnc"],
        "icon": "{self}/hooks/icons/houdini.png",
        "type_display": "Houdini Scene"
    },
    "file.maya": {
        "extensions": ["ma", "mb"],
        "icon": "{self}/hooks/icons/maya.png",
        "type_display": "Maya Scene"
    },
    "file.nuke": {
        "extensions": ["nk"],
        "icon": "{self}/hooks/icons/nuke.png",
        "type_display": "Nuke Script"
    },
    "file.photoshop": {
        "extensions": ["psd", "psb"],
        "icon": "{self}/hooks/icons/photoshop.png",
        "type_display": "Photoshop Image"
    },
    "file.render": {
        "extensions": ["dpx", "exr"],
        "icon": "{self}/hooks/icons/image.png",
        "type_display": "Rendered Image"
    },
    "file.texture": {
        "extensions": ["tif", "tiff", "tx", "tga", "dds", "rat"],
        "icon": "{self}/hooks/icons/texture.png",
        "type_display": "Texture Image"
    },
    "file.image": {
        "extensions": ["jpeg", "jpg", "png"],
        "icon": "{self}/hooks/icons/image.png",
        "type_display": "Image"
    },
    "file.video": {
        "extensions": ["mov", "mp4"],
        "icon": "{self}/hooks/icons/video.png",
        "type_display": "Movie"
    }
}


class FileCollectorPlugin(HookBaseClass):
    """
    A basic collector that handles files and general objects.

    This collector hook is used to collect individual files that are browsed or
    dragged and dropped into the Publish2 UI. It can also be subclassed by other
    collectors responsible for creating items for a file to be published such as
    the current Maya session file.

    This plugin centralizes the logic for collecting a file, including
    determining how to display the file for publishing (based on the file
    extension).

    In addition to creating an item to publish, this hook will set the following
    properties on the item::

        path - The path to the file to publish. This could be a path
            representing a sequence of files (including a frame specifier).

        sequence_paths - If the item represents a collection of files, the
            plugin will populate this property with a list of files matching
            "path".

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
        schema = super(FileCollectorPlugin, self).settings_schema
        schema["Item Types"]["default_value"] = DEFAULT_ITEM_TYPES
        schema["Item Types"]["values"]["items"] = {
            "extensions": {
                "type": "list",
                "values": {
                    "type": "str",
                    "description": "A string pattern to match a file extension."
                },
                "description": "A list of file extensions that this item type is interested in."
            },
            "icon": {
                "type": "config_path",
                "description": ""
            },
            "type_display": {
                "type": "str",
                "description": ""
            }
        }
        schema["Item Types"]["description"] = (
            "Dictionary of file type info that allows the basic "
            "collector to identify common production file types and "
            "associate them with a display name, item type, and config "
            "icon."
        )
        return schema

    def process_current_session(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        # default implementation does not do anything
        pass


    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """

        # handle files and folders differently
        if os.path.isdir(path):
            return self._collect_folder(parent_item, path)
        else:
            return self._collect_file(parent_item, path)


    def _collect_file(self, parent_item, path):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :param frame_sequence: Treat the path as a part of a sequence
        :returns: The item that was created
        """
        publisher = self.parent

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # Check to see if the input path contains a frame_spec
        frame_path = publisher.util.get_path_for_frame(path, 1001)
        if frame_path:
            # If so, set the seq_path equal to input path
            seq_path = path
        else:
            # Else check if the input path contains a frame number
            seq_path = publisher.util.get_frame_sequence_path(path)

        seq_files = []
        is_sequence = False
        if seq_path:

            # find files that match the pattern
            seq_pattern = publisher.util.get_path_for_frame(seq_path, "*")
            seq_files = [f for f in glob.iglob(seq_pattern) if os.path.isfile(f)]

            # Sort the resulting list
            seq_files.sort()

            # Set path to seq_path
            path = seq_path
            is_sequence = True

        # Make sure file(s) exist on disk
        if is_sequence:
            if not seq_files:
                self.logger.warn("File sequence does not exist for '%s'. Skipping" % path)
                return
        else:
            if not os.path.exists(path):
                self.logger.warn("File does not exist for '%s'. Skipping" % path)
                return

        return self._add_file_item(parent_item, path, is_sequence, seq_files)


    def _collect_folder(self, parent_item, folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        folder = sgtk.util.ShotgunPath.normalize(folder)

        publisher = self.parent
        frame_sequences = publisher.util.get_frame_sequences(folder, SEQ_EXTENSIONS_LIST)

        file_items = []
        for path, seq_files in frame_sequences:
            file_items += filter(None, [self._add_file_item(parent_item, path, True, seq_files)])

        if not file_items:
            self.logger.warn("No file sequences found in: %s" % (folder,))

        return file_items


    def _add_file_item(self, parent_item, path, is_sequence=False, seq_files=None):
        """
        Creates a file item
        """
        publisher = self.parent

        # get info for the extension
        item_info = self._get_item_info(path, is_sequence)

        icon_path = item_info["icon_path"]
        item_type = item_info["item_type"]
        type_display = item_info["type_display"]

        display_name = publisher.util.get_publish_name(path)

        # create and populate the item
        file_item = parent_item.create_item(
            item_type,
            type_display,
            display_name
        )

        # Set the icon path
        file_item.set_icon_from_path(icon_path)

        # if the supplied path is an image, use the path as the thumbnail.
        if (item_type.startswith("file.image") or
            item_type.startswith("file.texture") or
            item_type.startswith("file.render")):

            if is_sequence:
                file_item.set_thumbnail_from_path(seq_files[0])
            else:
                file_item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        file_item.properties["path"] = path

        file_item.properties["is_sequence"] = is_sequence
        if is_sequence:
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            file_item.properties["sequence_paths"] = seq_files
            file_info = (
                "The following files were collected:<br>"
                "<pre>%s</pre>" % (pprint.pformat(seq_files),)
            )
        else:
            file_info = (
                "The following file was collected:<br>"
                "<pre>%s</pre>" % (path,)
            )

        self.logger.info(
            "Collected item: %s" % display_name,
            extra={
                "action_show_more_info": {
                    "label": "Show File(s)",
                    "tooltip": "Show the collected file(s)",
                    "text": file_info
                }
            }
        )

        return file_item


    def _get_item_info(self, path, is_sequence):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param path: The file path to identify type info for

        :return: A dictionary of information about the item to create::

            # path = "/path/to/some/file.0001.exr"

            {
                "item_type": "file.image.sequence",
                "type_display": "Rendered Image Sequence",
                "icon_path": "/path/to/some/icons/folder/image_sequence.png",
            }

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """
        publisher = self.parent

        # extract the components of the supplied path
        file_info = publisher.util.get_file_path_components(path)
        extension = file_info["extension"]
        filename = file_info["filename"]

        # default values used if no specific type can be determined
        type_display = "File"
        item_type = "file.unknown"
        default_icon = "{self}/hooks/icons/file.png"

        # keep track if a common type was identified for the extension
        common_type_found = False

        # look for the extension in the common file type info dict
        for item in self.settings["Item Types"].value.iteritems():
            item_type = item[0]
            type_info = item[1]

            if extension in type_info["extensions"]:
                # found the extension in the common types lookup. extract the
                # item type, icon name.
                type_display = type_info["type_display"]
                icon_path = type_info["icon"]
                common_type_found = True
                break

        if not common_type_found:
            # no common type match. try to use the mimetype category. this will
            # be a value like "image/jpeg" or "video/mp4". we'll extract the
            # portion before the "/" and use that for display.
            (category_type, _) = mimetypes.guess_type(filename)

            if category_type:

                # mimetypes.guess_type can return unicode strings depending on
                # the system's default encoding. If a unicode string is
                # returned, we simply ensure it's utf-8 encoded to avoid issues
                # with toolkit, which expects utf-8
                if isinstance(category_type, unicode):
                    category_type = category_type.encode("utf-8")

                # the category portion of the mimetype
                category = category_type.split("/")[0]

                type_display = "%s File" % (category.title(),)
                item_type = "file.%s" % (category,)
                icon_path = "{self}/hooks/icons/%s.png" % (category,)

        # construct a full path to the icon given the name defined above
        icon_path = publisher.expand_path(icon_path)
        if not os.path.exists(icon_path):
            icon_path = publisher.expand_path(default_icon)

        if is_sequence:
            # if the supplied image path is part of a sequence. alter the
            # type info to account for this.
            type_display = "%s Sequence" % (type_display,)
            item_type = "%s.%s" % (item_type, "sequence")
            icon_path = "{self}/hooks/icons/image_sequence.png"

        # everything should be populated. return the dictionary
        return dict(
            icon_path=icon_path,
            item_type=item_type,
            type_display=type_display
        )


def _build_seq_extensions_list():

    file_types = ["file.photoshop", "file.render", "file.texture", "file.image"]
    extensions = set()

    for file_type in file_types:
        extensions.update(DEFAULT_ITEM_TYPES[file_type]["extensions"])

    # get all the image mime type extensions as well
    mimetypes.init()
    types_map = mimetypes.types_map
    for (ext, mimetype) in types_map.iteritems():
        if mimetype.startswith("image/"):
            extensions.add(ext.lstrip("."))

    return list(extensions)

SEQ_EXTENSIONS_LIST = _build_seq_extensions_list()
