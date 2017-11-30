# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import copy
import traceback
import sgtk
from contextlib import contextmanager
from sgtk.platform.qt import QtCore, QtGui
from sgtk.platform.bundle import resolve_setting_value
from .setting import *

logger = sgtk.platform.get_logger(__name__)

class PluginBase(object):
    """
    A base class for functionality common to plugin hooks (collectors and
    publish plugins).

    Each object reflects an instance in the app configuration.
    """

    def __init__(self, path, settings, logger):
        """
        :param path: Path to the collector hook
        :param settings: Dictionary of collector-specific settings
        :param logger: a logger object that will be used by the hook
        """
        self._logger = logger
        self._bundle = sgtk.platform.current_bundle()

        # create an instance of the hook
        self._base_hook_path = ':'.join(('{self}/base.py', self._base_hook_path))

        hook_path = ':'.join((self._base_hook_path, self._path))
        self._hook_instance = self._bundle.create_hook_instance(hook_path)

        try:
            self._settings_schema = self._hook_instance.settings_schema
        except NotImplementedError as e:
            # property not defined by the hook
            self._logger.error("No settings_schema defined by hook: %s" % self)
            self._settings_schema = {}

        # kick things off
        try:
            self._settings = self.validate_and_resolve_settings(settings)
        except Exception as e:
            error_msg = traceback.format_exc()
            self._logger.error(
                "Error validating settings for plugin %s in environment '%s': %s" %
                (self, self._bundle.env.name, error_msg)
            )
            self._settings = {}

        # add settings to cache
        settings_cache.add(self, self._bundle.context, self._settings)

        # pass the settings dict to the hook
        if hasattr(self._hook_instance.__class__, "settings"):
            self._hook_instance.settings = self._settings

    def __repr__(self):
        """
        String representation
        """
        return "<%s %s>" % (self.__class__.__name__, self._path)

    @property
    def logger(self):
        """
        returns the plugin logger
        """
        return self._logger

    @property
    def settings(self):
        """
        returns a dict of resolved raw settings given the current state
        """
        return self._settings

    def validate_and_resolve_settings(self, settings):
        """
        Init helper method.

        Validates plugin settings and creates Setting objects
        that can be accessed from the settings property.
        """
        new_settings = {}

        # Settings schema will be in the form:
        # "setting_a": {
        #     "type": "int",
        #     "default": 5,
        #     "description": "foo bar baz"
        # },

        for setting_name, setting_schema in self._settings_schema.iteritems():

            # Resolve the setting value using the supplied schema
            # This will also validate if setting is missing but required
            value = resolve_setting_value(
                self._bundle.sgtk,
                self._bundle._get_engine_name(),
                setting_schema,
                settings,
                setting_name,
                None,
                self._bundle
            )

            setting = Setting(
                setting_name,
                data_type=setting_schema.get("type"),
                default_value=setting_schema.get("default_value"),
                description=setting_schema.get("description")
            )
            setting.value = value

            new_settings[setting_name] = setting

        return new_settings


class PublishPlugin(PluginBase):
    """
    Class that wraps around a publishing plugin hook

    Each plugin object reflects an instance in the
    app configuration.
    """

    def __init__(self, name, path, settings, logger):
        """
        :param name: Name to be used for this plugin instance
        :param path: Path to publish plugin hook
        :param settings: Dictionary of plugin-specific settings
        :param logger: a logger object that will be used by the hook
        """
        # all plugins need a hook and a name
        self._name = name
        self._path = path

        self._tasks = []

        self._base_hook_path = '{self}/publish.py'
        hook_path = ':'.join((self._base_hook_path, self._path))

        super(PublishPlugin, self).__init__(hook_path, settings, logger)

        self._icon_pixmap = self._load_plugin_icon()

    def _load_plugin_icon(self):
        """
        Loads the icon defined by the hook.

        :returns: QPixmap or None if not found
        """
        # load plugin icon
        pixmap = None
        try:
            icon_path = self._hook_instance.icon
            try:
                pixmap = QtGui.QPixmap(icon_path)
            except Exception, e:
                self._logger.warning(
                    "%r: Could not load icon '%s': %s" % (self, icon_path, e)
                )
        except AttributeError:
            # plugin does not have an icon
            pass

        # load default pixmap if hook doesn't define one
        if pixmap is None:
            pixmap = QtGui.QPixmap(":/tk_multi_publish2/item.png")

        return pixmap

    @property
    def name(self):
        """
        The name of this plugin instance
        """
        return self._name

    @property
    def tasks(self):
        """
        Tasks associated with this publish plugin.
        """
        return self._tasks

    def add_task(self, task):
        """
        Adds a task to this publish plugin.

        :param task: Task instance to add.
        """
        self._tasks.append(task)

    @property
    def plugin_name(self):
        """
        The name of the publish plugin.
        Always a string.
        """
        value = None
        try:
            value = self._hook_instance.name
        except AttributeError:
            pass

        return value or "Untitled Integration."

    @property
    def description(self):
        """
        The decscription of the publish plugin.
        Always a string.
        """
        value = None
        try:
            value = self._hook_instance.description
        except AttributeError:
            pass

        return value or "No detailed description provided."

    @property
    def item_filters(self):
        """
        The item filters defined by this plugin
        or [] if none have been defined.
        """
        try:
            return self._hook_instance.item_filters
        except AttributeError:
            return []

    @property
    def has_custom_ui(self):
        """
        Checks if a plugin has a custom widget.

        :returns: ``True`` if the plugin supports ``create_settings_widget``,
            ``get_ui_settings`` and ``set_ui_settings``,``False`` otherwise.
        """
        return all(
            hasattr(self._hook_instance, attr)
            for attr in ["create_settings_widget", "get_ui_settings", "set_ui_settings"]
        )

    @property
    def icon(self):
        """
        The associated icon, as a pixmap, or None if no pixmap exists.
        """
        return self._icon_pixmap

    def run_create_settings_widget(self, parent):
        """
        Creates a custom widget to edit a plugin's settings.

        :param parent: Parent widget
        :type parent: :class:`QtGui.QWidget`
        """
        with self._handle_plugin_error(None, "Error laying out widgets: %s"):
            return self._hook_instance.create_settings_widget(parent)

    def run_get_ui_settings(self, parent):
        """
        Retrieves the settings from the custom UI.

        :param parent: Parent widget
        :type parent: :class:`QtGui.QWidget`
        """
        with self._handle_plugin_error(None, "Error reading settings from UI: %s"):
            return self._hook_instance.get_ui_settings(parent)

    def run_set_ui_settings(self, parent, settings):
        """
        Provides a list of settings from the custom UI. It is the responsibility of the UI
        handle different values for the same setting.

        :param parent: Parent widget
        :type parent: :class:`QtGui.QWidget`

        :param settings: List of dictionary of settings as python literals.
        """
        with self._handle_plugin_error(None, "Error writing settings to UI: %s"):
            self._hook_instance.set_ui_settings(parent, settings)


    def init_task_settings(self, item):
        """
        Initializes an instance of this plugin's settings for the item's context,
        either from the settings cache, or from the raw app settings. Then passes
        those settings to the hook init_task_settings for any customization.

        :param item: Item to analyze
        :returns: dictionary of task settings
        """
        try:
            # Check the cache to see if we already have setting for this plugin/context pair
            settings = settings_cache.get(self, item.context)
            if not settings:
                # If they aren't in the cache, then go get the raw settings
                settings = get_raw_plugin_settings(self, item.context)

                # Resolve the settings
                settings = self.validate_and_resolve_settings(settings)

                # Add them to the cache
                settings_cache.add(self, item.context, settings)

            # Make a copy since other tasks may be referencing the same settings
            settings = copy.deepcopy(settings)

            return self._hook_instance.init_task_settings(settings, item)

        except Exception:
            error_msg = traceback.format_exc()
            self._logger.error(
                "Error running init_task_settings for %s" % self,
                extra = _get_error_extra_info(error_msg)
            )
            return {}
        finally:
            # give qt a chance to do stuff
            QtCore.QCoreApplication.processEvents()

    def run_accept(self, task_settings, item):
        """
        Executes the hook accept method for the given item

        :param item: Item to analyze
        :returns: dictionary with boolean keys accepted/visible/enabled/checked
        """
        try:
            return self._hook_instance.accept(task_settings, item)
        except Exception:
            error_msg = traceback.format_exc()
            self._logger.error(
                "Error running accept for %s" % self,
                extra = _get_error_extra_info(error_msg)
            )
            return {"accepted": False}
        finally:
            # give qt a chance to do stuff
            QtCore.QCoreApplication.processEvents()

    def run_validate(self, task_settings, item):
        """
        Executes the validation logic for this plugin instance.

        :param settings: Dictionary of settings
        :param item: Item to analyze
        :return: True if validation passed, False otherwise.
        """
        status = False
        with self._handle_plugin_error(None, "Error Validating: %s"):
            status = self._hook_instance.validate(task_settings, item)

        # check that we are not trying to publish to a site level context
        if item.context.project is None:
            status = False
            self._logger.error("Please link '%s' to a Shotgun object and task!" % item.name)

        if status:
            self._logger.info("Validation successful!")
        else:
            self._logger.error("Validation failed.")

        return status

    def run_publish(self, task_settings, item):
        """
        Executes the publish logic for this plugin instance.

        :param settings: Dictionary of settings
        :param item: Item to analyze
        """
        with self._handle_plugin_error("Publish complete!", "Error publishing: %s"):
            self._hook_instance.publish(task_settings, item)

    def run_finalize(self, task_settings, item):
        """
        Executes the finalize logic for this plugin instance.

        :param settings: Dictionary of settings
        :param item: Item to analyze
        """
        with self._handle_plugin_error("Finalize complete!", "Error finalizing: %s"):
            self._hook_instance.finalize(task_settings, item)

    @contextmanager
    def _handle_plugin_error(self, success_msg, error_msg):
        """
        Creates a scope that will properly handle any error raised by the plugin
        while the scope is executed.

        .. note::
            Any exception raised by the plugin is bubbled up to the caller.

        :param str success_msg: Message to be displayed if there is no error.
        :param str error_msg: Message to be displayed if there is an error.
        """

        try:
            # Execute's the code inside the with statement. Any errors will be
            # caught and logged and the events will be processed
            yield
        except Exception as e:
            exception_msg = traceback.format_exc()
            self._logger.error(
                error_msg % (e,),
                extra=_get_error_extra_info(exception_msg)
            )
            raise
        else:
            if success_msg:
                self._logger.info(success_msg)
        finally:
            QtCore.QCoreApplication.processEvents()


class CollectorPlugin(PluginBase):
    """
    Class that wraps around a collector hook

    Each collector object reflects an instance in the app configuration.
    """
    def __init__(self, path, settings, logger):
        """
        :param name: Name to be used for this plugin instance
        :param path: Path to publish plugin hook
        :param settings: Dictionary of plugin-specific settings
        :param logger: a logger object that will be used by the hook
        """
        # all collector plugins need a hook
        self._path = path

        self._base_hook_path = '{self}/collector.py'
        hook_path = ':'.join((self._base_hook_path, self._path))

        super(CollectorPlugin, self).__init__(hook_path, settings, logger)

    def run_process_current_session(self, item):
        """
        Executes the hook process_current_session method

        :param item: Item to parent collected items under.

        :returns: None (item creation handles parenting)
        """
        try:
            return self._hook_instance.process_current_session(item)
        except Exception, e:
            error_msg = traceback.format_exc()
            logger.error(
                "Error running process_current_session for %s. %s" %
                (self, error_msg)
            )

    def run_process_file(self, item, path):
        """
        Executes the hook process_file method

        :param item: Item to parent collected items under.
        :param path: The path of the file to collect

        :returns: None (item creation handles parenting)
        """
        try:
            return self._hook_instance.process_file(item, path)
        except Exception, e:
            error_msg = traceback.format_exc()
            logger.error(
                "Error running process_file for %s. %s" %
                (self, error_msg)
            )

def _get_error_extra_info(error_msg):
    """
    A little wrapper to return a dictionary of data to show a button in the
    publisher with the supplied error message.

    :param error_msg: The error message to display.
    :return: An logging "extra" dictionary to show the error message.
    """

    return {
        "action_show_more_info": {
            "label": "Error Details",
            "tooltip": "Show the full error tack trace",
            "text": "<pre>%s</pre>" % (error_msg,)
        }
    }

