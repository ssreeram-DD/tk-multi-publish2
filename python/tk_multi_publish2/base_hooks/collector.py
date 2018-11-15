# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import copy
import sgtk

from .base import PluginBase

class CollectorPlugin(PluginBase):
    """
    This class defines the required interface for a collector plugin.
    Collectors are used to gather individual files that are loaded via the
    file browser or dragged and dropped into the Publish2 UI. It is also used
    to gather items to be published within the current DCC session.
    """

    @property
    def id(self):
        """
        Unique string identifying this plugin.
        """
        return self._id

    @id.setter
    def id(self, new_id):
        """
        Allows to set the unique string identifying this plugin.
        """
        self._id = new_id

    ############################################################################
    # Collector properties

    @property
    def settings_schema(self):
        """
        A :class:`dict` defining the configuration interface for this collector.

        The values configured for the collector will be supplied via settings
        parameter in the :func:`process_current_session` and
        :func:`process_file` methods.

        The dictionary can include any number of settings required by the
        collector, and takes the form::

            {
                <setting_name>: {
                    "type": <type>,
                    "default": <default>,
                    "description": <description>
                },
                <setting_name>: {
                    "type": <type>,
                    "default": <default>,
                    "description": <description>
                },
                ...
            }

        The keys in the dictionary represent the names of the settings. The
        values are a dictionary comprised of 3 additional key/value pairs.

        * ``type``: The type of the setting. This should correspond to one of
          the data types that toolkit accepts for app and engine settings such
          as ``hook``, ``template``, ``string``, etc.
        * ``default``: The default value for the settings. This can be ``None``.
        * ``description``: A description of the setting as a string.

        Example implementation:

        .. code-block:: python

            @property
            def settings(self):
                return {
                    "Work Template": {
                        "type": "template",
                        "default": None,
                        "description": "A work file template required by this collector."
                    },
                    "Exclude Objects": {
                        "type": "list",
                        "default": ["obj1", "obj2", "obj3"],
                        "description": "A list of objects to ignore."
                    }
                }

        The settings are exposed via the ``collector_settings`` setting in the
        app's configuration. Example::

            collector_settings:
                Work Template: my_work_template
                Exclude Objects: [obj1, obj4]

        .. note:: See the hooks defined in the publisher app's ``hooks/`` folder
           for additional example implementations.
        """
        return {
            "Item Types": {
                "type": "dict",
                "values": {
                    "type": "dict",
                    "items": {
                        "icon_path": {
                            "type": "config_path",
                            "description": ""
                        },
                        "type_display": {
                            "type": "str",
                            "description": ""
                        }
                    },
                },
                "default_value": {},
                "description": (
                    "Dictionary of item types that the collector will attempt to "
                    "match and create instances of."
                )
            }
        }

    ############################################################################
    # Collection methods

    def process_current_session(self, settings, parent_item):
        """
        This method analyzes the current engine session and creates a hierarchy
        of items for publishing.

        A typical implementation of this method would create an item that
        represents the current session (e.g. the current Maya file) or all open
        documents in a multi-document scenario (such as Photoshop). Top level
        items area created as children of the supplied ``parent_item``
        (a :ref:`publish-api-item` instance).

        Any additional items, specific to the current session, can then be
        created as children of the session item. This is not a requirement
        however. You could, for example, create a flat list of items, all
        sharing the same parent.

        The image below shows a Maya scene item with a child item that
        represents a playblast to be published. Each of these items has one or
        more publish tasks attached to them.

        .. image:: ./resources/collected_session_item.png

        |

        The ``settings`` argument is a dictionary where the keys are the names
        of the settings defined by the :func:`settings` property and the values
        are :ref:`publish-api-setting` instances as configured for this
        instance of the publish app.

        To create items within this method, use the
        :meth:`~.api.PublishItem.create_item` method available on the supplied
        ``parent_item``.

        Example Maya implementation:

        .. code-block:: python

            def process_current_session(settings, parent_item):

                path = cmds.file(query=True, sn=True)

                session_item = parent_item.create_item(
                    "maya.session",
                    "Maya Session",
                    os.path.basename(path)
                )

                # additional work here to prep the session item such as defining
                # an icon, populating the properties dictionary, etc.
                session_item.properties["path"] = path

                # collect additional file types, parented under the session
                self._collect_geometry(settings, session_item)

        .. note:: See the hooks defined in the publisher app's ``hooks/`` folder
           for additional example implementations.

        :param dict settings: A dictionary of configured
            :ref:`publish-api-setting` objects for this collector.
        :param parent_item: The root :ref:`publish-api-item` instance to
            collect child items for.
        """
        raise NotImplementedError


    def process_file(self, settings, parent_item, path):
        """
        This method creates one or more items to publish for the supplied file
        path.

        The image below shows a collected text file item to be published.

        .. image:: ./resources/collected_file.png

        |

        A typical implementation of this method involves processing the supplied
        path to determine what type of file it is and how to display it before
        creating the item to publish.

        The ``settings`` argument is a dictionary where the keys are the names
        of the settings defined by the :func:`settings` property and the values
        are :ref:`publish-api-setting` instances as
        configured for this instance of the publish app.

        To create items within this method, use the
        :meth:`~.api.PublishItem.create_item` method available on the supplied
        ``parent_item``.

        Example implementation:

        .. code-block:: python

            def process_file(settings, parent_item, path):

                # make sure the path is normalized. no trailing separator,
                # separators are appropriate for the current os, no double
                # separators, etc.
                path = sgtk.util.ShotgunPath.normalize(path)

                # do some processing of the file to determine its type, and how
                # to display it.
                ...

                # create and populate the item
                file_item = parent_item.create_item(
                    item_type,
                    type_display,
                    os.path.basename(path)
                )

                # additional work here to prep the session item such as defining
                # an icon, populating the properties dictionary, etc.
                session_item.properties["path"] = path

        .. note:: See the hooks defined in the publisher app's ``hooks/`` folder
           for additional example implementations.

        :param dict settings: A dictionary of configured
            :ref:`publish-api-setting` objects for this collector.
        :param parent_item: The root :ref:`publish-api-item` instance to
            collect child items for.
        :param path: A string representing the file path to analyze
        """
        raise NotImplementedError


    def on_context_changed(self, settings, item):
        """
        Callback to update the item on context changes.

        :param dict settings: A dictionary of configured
            :ref:`publish-api-setting` objects for this
            collector.
        :param parent_item: The current :ref:`publish-api-item` instance
            whose :class:`sgtk.Context` has been updated.
        """
        raise NotImplementedError


    ############################################################################
    # protected helper methods

    def _add_item(self, settings, parent_item, item_name, item_type, context=None, properties=None):
        """
        Creates a generic item

        :param dict settings: Configured settings for this collector
        :param parent_item: parent item instance
        :param item_name: The name of the item instance
        :param item_type: The type of the item instance
        :param context: The :class:`sgtk.Context` to set for the item
        :param properties: The dict of initial properties for the item

        :returns: The item that was created and its item_info dictionary
        """
        publisher = self.parent

        # Get this item's info from the settings object
        item_info = self._get_item_type_info(settings, item_type)

        type_display = item_info["type_display"]
        icon_path    = item_info["icon_path"]

        # create and populate the item
        item = parent_item.create_item(
            item_type,
            type_display,
            item_name,
            collector=self.plugin,
            context=context,
            properties=properties
        )

        # construct a full path to the icon given the name defined above
        icon_path = publisher.expand_path(icon_path)

        # Set the icon path
        item.set_icon_from_path(icon_path)

        return item


    def _get_item_type_info(self, settings, item_type):
        """
        Return the dictionary corresponding to this item's 'Item Types' settings.

        :param dict settings: Configured settings for this collector
        :param item_type: The type of Item to identify info for

        :return: A dictionary of information about the item to create::

            # item_type = "mari.session"

            {
                "type_display": "Mari Session",
                "icon_path": "/path/to/some/icons/folder/mari.png",
            }
        """
        # default values used if no specific type can be determined
        default_item_info = {
            'type_display' : 'Item',
            'icon_path' : '{self}/hooks/icons/file.png'
        }

        item_types = copy.deepcopy(settings["Item Types"].value)
        return item_types.get(item_type, default_item_info)
