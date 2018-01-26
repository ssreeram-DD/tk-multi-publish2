# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'item_widget.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_ItemWidget(object):
    def setupUi(self, ItemWidget):
        ItemWidget.setObjectName("ItemWidget")
        ItemWidget.resize(290, 45)
        ItemWidget.setMinimumSize(QtCore.QSize(0, 45))
        self.verticalLayout = QtGui.QVBoxLayout(ItemWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame = QtGui.QFrame(ItemWidget)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtGui.QHBoxLayout(self.frame)
        self.horizontalLayout.setSpacing(8)
        self.horizontalLayout.setContentsMargins(4, 2, 2, 2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.expand_indicator = QtGui.QToolButton(self.frame)
        self.expand_indicator.setMinimumSize(QtCore.QSize(16, 16))
        self.expand_indicator.setMaximumSize(QtCore.QSize(16, 16))
        self.expand_indicator.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/tk_multi_publish2/down_arrow.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.expand_indicator.setIcon(icon)
        self.expand_indicator.setObjectName("expand_indicator")
        self.horizontalLayout.addWidget(self.expand_indicator)
        self.icon = QtGui.QLabel(self.frame)
        self.icon.setMinimumSize(QtCore.QSize(32, 32))
        self.icon.setMaximumSize(QtCore.QSize(30, 30))
        self.icon.setText("")
        self.icon.setScaledContents(True)
        self.icon.setObjectName("icon")
        self.horizontalLayout.addWidget(self.icon)
        self.header = QtGui.QLabel(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.header.sizePolicy().hasHeightForWidth())
        self.header.setSizePolicy(sizePolicy)
        self.header.setObjectName("header")
        self.horizontalLayout.addWidget(self.header)
        self.status = QtGui.QToolButton(self.frame)
        self.status.setMinimumSize(QtCore.QSize(30, 30))
        self.status.setMaximumSize(QtCore.QSize(30, 30))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/tk_multi_publish2/status_validate.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.status.setIcon(icon1)
        self.status.setIconSize(QtCore.QSize(24, 24))
        self.status.setObjectName("status")
        self.horizontalLayout.addWidget(self.status)
        self.handle_stack = QtGui.QStackedWidget(self.frame)
        self.handle_stack.setMinimumSize(QtCore.QSize(22, 22))
        self.handle_stack.setMaximumSize(QtCore.QSize(22, 22))
        self.handle_stack.setObjectName("handle_stack")
        self.drag = QtGui.QWidget()
        self.drag.setObjectName("drag")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.drag)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.drag_handle = QtGui.QLabel(self.drag)
        self.drag_handle.setMinimumSize(QtCore.QSize(16, 16))
        self.drag_handle.setMaximumSize(QtCore.QSize(16, 16))
        self.drag_handle.setCursor(QtCore.Qt.OpenHandCursor)
        self.drag_handle.setText("")
        self.drag_handle.setPixmap(QtGui.QPixmap(":/tk_multi_publish2/drag_handle.png"))
        self.drag_handle.setScaledContents(True)
        self.drag_handle.setObjectName("drag_handle")
        self.horizontalLayout_2.addWidget(self.drag_handle)
        self.handle_stack.addWidget(self.drag)
        self.lock = QtGui.QWidget()
        self.lock.setObjectName("lock")
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.lock)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.locked_handle = QtGui.QLabel(self.lock)
        self.locked_handle.setMinimumSize(QtCore.QSize(16, 16))
        self.locked_handle.setMaximumSize(QtCore.QSize(16, 16))
        self.locked_handle.setText("")
        self.locked_handle.setScaledContents(True)
        self.locked_handle.setObjectName("locked_handle")
        self.horizontalLayout_3.addWidget(self.locked_handle)
        self.handle_stack.addWidget(self.lock)
        self.horizontalLayout.addWidget(self.handle_stack)
        self.checkbox = QtGui.QCheckBox(self.frame)
        self.checkbox.setText("")
        self.checkbox.setObjectName("checkbox")
        self.horizontalLayout.addWidget(self.checkbox)
        self.horizontalLayout.setStretch(2, 10)
        self.verticalLayout.addWidget(self.frame)

        self.retranslateUi(ItemWidget)
        self.handle_stack.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(ItemWidget)

    def retranslateUi(self, ItemWidget):
        ItemWidget.setWindowTitle(QtGui.QApplication.translate("ItemWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.header.setText(QtGui.QApplication.translate("ItemWidget", "<big>Alembic Caches</big><br>foo", None, QtGui.QApplication.UnicodeUTF8))
        self.status.setToolTip(QtGui.QApplication.translate("ItemWidget", "Click for details", None, QtGui.QApplication.UnicodeUTF8))
        self.status.setText(QtGui.QApplication.translate("ItemWidget", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.drag_handle.setToolTip(QtGui.QApplication.translate("ItemWidget", "Drag & drop enabled for changing this item\'s context", None, QtGui.QApplication.UnicodeUTF8))
        self.locked_handle.setToolTip(QtGui.QApplication.translate("ItemWidget", "Context change is not allowed for this item", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
