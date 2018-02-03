# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import sgtk
from sgtk.platform.qt import QtCore, QtGui
from .ui.context_widget import Ui_ContextWidget
from .custom_widget_base import CustomTreeWidgetBase


logger = sgtk.platform.get_logger(__name__)


class CustomTreeWidgetContext(CustomTreeWidgetBase):
    """
    Context display widget
    """

    def __init__(self, tree_node, parent=None):
        """
        :param parent: The parent QWidget for this control
        """
        super(CustomTreeWidgetContext, self).__init__(tree_node, parent)

        # set up the UI
        self.ui = Ui_ContextWidget()
        self.ui.setupUi(self)
        self.ui.checkbox.stateChanged.connect(self._on_checkbox_click)
        self.ui.checkbox.setTristate(True)
        self.ui.checkbox.nextCheckState = self.nextCheckState

    def nextCheckState(self):
        """
        Callback that handles QT tri-state logic
        """
        # QT tri-state logic is a little odd, see the docs for more
        # details.
        state = self.ui.checkbox.checkState()
        if state == QtCore.Qt.Checked:
            self.ui.checkbox.setCheckState(QtCore.Qt.Unchecked)
        elif state == QtCore.Qt.PartiallyChecked:
            self.ui.checkbox.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.ui.checkbox.setCheckState(QtCore.Qt.Checked)

    def _on_checkbox_click(self, state):
        """
        Callback that fires when the user clicks the checkbox
        """
        self._tree_node.set_check_state(state)

    @property
    def icon(self):
        """
        The icon pixmap associated with this item
        """
        return None

    def set_icon(self, pixmap):
        """
        Set the icon to be used

        :param pixmap: Square icon pixmap to use
        """
        pass

    def set_status(self, status, message="", info_below=True):
        """
        Set the status for the plugin
        :param status: An integer representing on of the
            status constants defined by the class
        """
        pass
