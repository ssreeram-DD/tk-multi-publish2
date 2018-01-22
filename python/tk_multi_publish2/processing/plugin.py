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
from sgtk.platform.application import get_application
from sgtk.platform.engine import get_environment_from_context
from sgtk.platform import find_app_settings
from sgtk import TankError

from .setting import *

logger = sgtk.platform.get_logger(__name__)

class PluginBase(object):
    """
    A base class for functionality common to plugin hooks (collectors and
    publish plugins).

    Each object reflects an instance in the app configuration.
    """

    def __init__(self, path, logger):
        """
        :param path: Path to the collector hook
        :param logger: a logger object that will be used by the hook
        """
        self._logger = logger
        self._bundle = sgtk.platform.current_bundle()

        # create an instance of the hook
        hook_path = '{self}/base.py' + (":" + path if path else "")
        self._hook_instance = self._bundle.create_hook_instance(hook_path)

        try:
            self._settings_schema = self._hook_instance.settings_schema
        except NotImplementedError as e:
            # property not defined by the hook
            self._logger.error("No settings_schema defined by hook: %s" % self)
            self._settings_schema = {}

        # kick things off
        try:
            self._settings = self.build_settings_dict(self._bundle.context)
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

    @property
    def settings_schema(self):
        """
        returns a dict of resolved raw settings given the current state
        """
        return self._settings_schema

    def build_settings_dict(self, context):
        """
        Init helper method.

        Validates plugin settings and creates Setting objects
        that can be accessed from the settings property.

        Settings schema will be in the form:
            "setting_a": {
                "type": "int",
                "default": 5,
                "description": "foo bar baz"
            }
        """

        # Get the resolved settings for the plugin from the specified context
        resolved_settings = self._get_resolved_plugin_settings(context)

        new_settings = {}
        for setting_name, setting_schema in self._settings_schema.iteritems():

            setting = Setting(
                setting_name,
                data_type=setting_schema.get("type"),
                default_value=setting_schema.get("default_value"),
                description=setting_schema.get("description")
            )
            setting.value = resolved_settings[setting_name]

            new_settings[setting_name] = setting

        return new_settings

    def _get_resolved_plugin_settings(self, context):
        """
        Find and resolve settings for the plugin in the specified context

        :param context: Context in which to look for settings.

        :returns: The plugin settings for the given context or None.
        """
        app = self._bundle

        if not context:
            raise TankError("No context specified.")

        env = get_environment_from_context(app.sgtk, context)
        if not env:
            raise TankError("Cannot determine environment for context: %s" % context)

        # find settings for all instances of app in the environment picked for the given context:
        app_settings_list = find_app_settings(
            app.engine.name,
            app.name,
            app.sgtk,
            context,
            app.engine.instance_name
        )

        # No settings found, raise an error
        if not app_settings_list:
            raise TankError("Cannot find settings for %s in env: '%s' for context "
                "%s" % (app.name, env.name, context)
            )

        if len(app_settings_list) > 1:
            # There's more than one instance of that app for the engine instance, so we'll
            # need to deterministically pick one. We'll pick the one with the same
            # application instance name as the current app instance.
            for settings in app_settings:
                if settings.get("app_instance") == app.instance_name:
                    app_settings = settings
                    break
        else:
            app_settings = app_settings_list[0]

        if not app_settings:
            raise TankError(
                "Search for %s settings in env '%s' for context %s yielded too "
                "many results (%s), none named '%s'" % (app.name, env.name, context,
                ", ".join([s.get("app_instance") for s in app_settings_list]),
                app.instance_name)
            )

        new_env = app_settings["env_instance"]
        new_eng = app_settings["engine_instance"]
        new_app = app_settings["app_instance"]
        new_settings = app_settings["settings"]
        new_descriptor = new_env.get_app_descriptor(new_eng, new_app)

        # Create a new app instance from the new env / context
        new_app_obj = get_application(
                app.engine, 
                new_descriptor.get_path(), 
                new_descriptor, 
                new_settings, 
                new_app, 
                new_env,
                context)

        # Inject this plugin's schema for proper resolution
        resolved_settings = self._get_resolved_settings(new_app_obj)
        if not resolved_settings:
            raise TankError(
                "Definition for app '%s' in env '%s' is missing settings for plugin "
                "'%s' for context %s" % (new_app, new_env.name, self.name, context)
            )

        return resolved_settings


class PublishPlugin(PluginBase):
    """
    Class that wraps around a publishing plugin hook

    Each plugin object reflects an instance in the
    app configuration.
    """

    def __init__(self, name, path, logger):
        """
        :param name: Name to be used for this plugin instance
        :param path: Path to publish plugin hook
        :param logger: a logger object that will be used by the hook
        """
        # all plugins need a hook and a name
        self._name = name
        self._path = path or ""

        # Prepend hook path with publish plugin base class
        hook_path = '{self}/publish.py' + (":" + path if path else "")

        super(PublishPlugin, self).__init__(hook_path, logger)

        self._tasks = []
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

    def _get_resolved_settings(self, app_obj):
        """
        """
        # Inject this plugin's schema for proper resolution
        new_schema = copy.deepcopy(app_obj.descriptor.configuration_schema)        
        new_schema["publish_plugins"]["values"]["items"]["settings"]["items"] = self.settings_schema

        # Resolve the setting value, this also implicitly validates
        plugin_defs = resolve_setting_value(
                    app_obj.sgtk,
                    app_obj.engine.name,
                    new_schema["publish_plugins"],
                    app_obj.settings,
                    "publish_plugins",
                    None,
                    bundle=app_obj,
                    validate=True
                )

        # Now get the plugin settings matching this plugin
        for plugin_def in plugin_defs:
            if plugin_def["name"] == self.name:
                return plugin_def["settings"]

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


    def init_task_settings(self, item, context):
        """
        Initializes an instance of this plugin's settings for the item's context,
        either from the settings cache, or from the raw app settings. Then passes
        those settings to the hook init_task_settings for any customization.

        :param item: Item to analyze
        :returns: dictionary of task settings
        """
        try:
            # Check the cache to see if we already have setting for this plugin/context pair
            settings = settings_cache.get(self, context)
            if not settings:
                # If they aren't in the cache, then go get the settings for this context
                settings = self.build_settings_dict(context)

                # Add them to the cache
                settings_cache.add(self, context, settings)

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
        # check that we are not trying to publish to a site level context
        if item.context.task is None:
            status = False
            self._logger.error("Please link '%s' to a Shotgun entity and task!" % item.name)
        else:
            status = False
            with self._handle_plugin_error(None, "Error Validating: %s"):
                status = self._hook_instance.validate(task_settings, item)

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
    def __init__(self, path, logger):
        """
        :param name: Name to be used for this plugin instance
        :param path: Path to publish plugin hook
        :param settings: Dictionary of plugin-specific settings
        :param logger: a logger object that will be used by the hook
        """
        # all collector plugins need a hook
        self._path = path or ""

        # Prepend hook path with collector plugin base class
        hook_path = '{self}/collector.py' + (":" + path if path else "")

        super(CollectorPlugin, self).__init__(hook_path, logger)

    def run_process_current_session(self, item):
        """
        Executes the hook process_current_session method

        :param item: Item to parent collected items under.

        :returns: None (item creation handles parenting)
        """
        try:
            child_items = self._hook_instance.process_current_session(item)
            for item in child_items:
                # Run the item initialization for the current context
                self._hook_instance.on_context_changed(item)
            return child_items
        except Exception:
            error_msg = traceback.format_exc()
            self._logger.error(
                "Error running process_current_session for %s" % self,
                extra = _get_error_extra_info(error_msg)
            )
        finally:
            # give qt a chance to do stuff
            QtCore.QCoreApplication.processEvents()

    def run_process_file(self, item, path):
        """
        Executes the hook process_file method

        :param item: Item to parent collected items under.
        :param path: The path of the file to collect

        :returns: None (item creation handles parenting)
        """
        try:
            child_items = self._hook_instance.process_file(item, path)
            for item in child_items:
                # Run the item initialization for the current context
                self._hook_instance.on_context_changed(item)
            return child_items
        except Exception:
            error_msg = traceback.format_exc()
            self._logger.error(
                "Error running process_file for %s" % self,
                extra = _get_error_extra_info(error_msg)
            )
        finally:
            # give qt a chance to do stuff
            QtCore.QCoreApplication.processEvents()

    def _get_resolved_settings(self, app_obj):
        """
        """
        # Inject this plugin's schema for proper resolution
        new_schema = copy.deepcopy(app_obj.descriptor.configuration_schema)        
        new_schema["collector_settings"]["items"] = self.settings_schema

        # Resolve the setting value, this also implicitly validates
        resolved_settings = resolve_setting_value(
                    app_obj.sgtk,
                    app_obj.engine.name,
                    new_schema["collector_settings"],
                    app_obj.settings,
                    "collector_settings",
                    None,
                    bundle=app_obj,
                    validate=True
                )

        return resolved_settings


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

