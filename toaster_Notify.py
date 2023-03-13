from PyQt5 import QtCore, QtWidgets, QtGui


class QToaster(QtWidgets.QFrame):
    closed = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(QToaster, self).__init__(*args, **kwargs)
        QtWidgets.QHBoxLayout(self)

        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self.setStyleSheet(
            """
            QToaster {
                border: 0.5px solid gray;
                border-radius: 0px; 
                color: rgb(255, 255, 255);
                background-color: rgb(49, 54, 59);
            }
        """
        )
        # alternatively:
        self.setAutoFillBackground(True)
        self.setFrameShape(self.Box)

        self.timer = QtCore.QTimer(singleShot=True, timeout=self.hide)

        if self.parent():
            self.opacityEffect = QtWidgets.QGraphicsOpacityEffect(opacity=0)
            self.setGraphicsEffect(self.opacityEffect)
            self.opacityAni = QtCore.QPropertyAnimation(self.opacityEffect, b"opacity")
            # we have a parent, install an eventFilter so that when it's resized
            # the notification will be correctly moved to the right corner
            self.parent().installEventFilter(self)
        else:
            # there's no parent, use the window opacity property, assuming that
            # the window manager supports it; if it doesn't, this won'd do
            # anything (besides making the hiding a bit longer by half a second)
            self.opacityAni = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.opacityAni.setStartValue(0.0)
        self.opacityAni.setEndValue(1.0)
        self.opacityAni.setDuration(100)
        self.opacityAni.finished.connect(self.check_closed)

        self.corner = QtCore.Qt.TopLeftCorner
        self.margin = 3

    def check_closed(self):
        # if we have been fading out, we're closing the notification
        if self.opacityAni.direction() == self.opacityAni.Backward:
            self.close()

    def restore(self):
        # this is a "helper function", that can be called from mouseEnterEvent
        # and when the parent widget is resized. We will not close the
        # notification if the mouse is in or the parent is resized
        self.timer.stop()
        # also, stop the animation if it's fading out...
        self.opacityAni.stop()
        # ...and restore the opacity
        if self.parent():
            self.opacityEffect.setOpacity(1)
        else:
            self.setWindowOpacity(1)

    def hide(self):
        # start hiding
        self.opacityAni.setDirection(self.opacityAni.Backward)
        self.opacityAni.setDuration(500)
        self.opacityAni.start()

    def eventFilter(self, source, event):
        if source == self.parent() and event.type() == QtCore.QEvent.Resize:
            self.opacityAni.stop()
            parent_rect = self.parent().rect()
            geo = self.geometry()
            if self.corner == QtCore.Qt.TopLeftCorner:
                geo.moveTopLeft(
                    parent_rect.topLeft() + QtCore.QPoint(self.margin, self.margin)
                )
            elif self.corner == QtCore.Qt.TopRightCorner:
                geo.moveTopRight(
                    parent_rect.topRight() + QtCore.QPoint(-self.margin, self.margin)
                )
            elif self.corner == QtCore.Qt.BottomRightCorner:
                geo.moveBottomRight(
                    parent_rect.bottomRight()
                    + QtCore.QPoint(-self.margin, -self.margin)
                )
            else:
                geo.moveBottomLeft(
                    parent_rect.bottomLeft() + QtCore.QPoint(self.margin, -self.margin)
                )
            self.setGeometry(geo)
            self.restore()
            self.timer.start()
        return super(QToaster, self).eventFilter(source, event)

    def enterEvent(self, event):
        self.restore()

    def leaveEvent(self, event):
        self.timer.start()

    def closeEvent(self, event):
        # we don't need the notification anymore, delete it!
        self.deleteLater()

    def resizeEvent(self, event):
        super(QToaster, self).resizeEvent(event)
        # if you don't set a stylesheet, you don't need any of the following!
        if not self.parent():
            # there's no parent, so we need to update the mask
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(self.rect()).translated(-0.5, -0.5), 4, 4)
            self.setMask(
                QtGui.QRegion(path.toFillPolygon(QtGui.QTransform()).toPolygon())
            )
        else:
            self.clearMask()

    @staticmethod
    def show_message(
        parent,
        message,
        icon=QtWidgets.QStyle.PixelMetric,
        corner=QtCore.Qt.BottomLeftCorner,
        margin=85,
        closable=True,
        timeout=5000,
        desktop=False,
        parentWindow=True,
    ):
        if parent and parentWindow:
            parent = parent.window()

        if not parent or desktop:
            self = QToaster(None)
            self.setWindowFlags(
                self.windowFlags()
                | QtCore.Qt.FramelessWindowHint
                | QtCore.Qt.BypassWindowManagerHint
            )
            # This is a dirty hack!
            # parentless objects are garbage collected, so the widget will be
            # deleted as soon as the function that calls it returns, but if an
            # object is referenced to *any* other object it will not, at least
            # for PyQt (I didn't test it to a deeper level)
            self.__self = self

            current_screen = QtWidgets.QApplication.primaryScreen()
            if parent and parent.window().geometry().size().isValid():
                # the notification is to be shown on the desktop, but there is a
                # parent that is (theoretically) visible and mapped, we'll try to
                # use its geometry as a reference to guess which desktop shows
                # most of its area; if the parent is not a top level window, use
                # that as a reference
                reference = parent.window().geometry()
            else:
                # the parent has not been mapped yet, let's use the cursor as a
                # reference for the screen
                reference = QtCore.QRect(
                    QtGui.QCursor.pos() - QtCore.QPoint(4, 1), QtCore.QSize(100, 100)
                )
            max_area = 0
            for screen in QtWidgets.QApplication.screens():
                intersected = screen.geometry().intersected(reference)
                area = intersected.width() * intersected.height()
                if area > max_area:
                    max_area = area
                    current_screen = screen
            parent_rect = current_screen.availableGeometry()
        else:
            self = QToaster(parent)
            parent_rect = parent.rect()

        self.timer.setInterval(timeout)

        self.label = QtWidgets.QLabel(message)
        # self.label.setStyleSheet("color: rgb(255, 255, 255);")
        # font = QtGui.QFont()
        # font.setFamily("'Noto Sans'")
        # font.setPointSize(10)
        # font.setWeight(100)
        # self.label.setFont(font)
        self.layout().addWidget(self.label)

        if closable:
            self.closeButton = QtWidgets.QToolButton()
            self.layout().addWidget(self.closeButton)
            close_icon = self.style().standardIcon(
                QtWidgets.QStyle.SP_TitleBarCloseButton
            )
            self.closeButton.setIcon(close_icon)
            self.closeButton.setAutoRaise(True)
            self.closeButton.clicked.connect(self.close)

        self.timer.start()

        # raise the widget and adjust its size to the minimum
        self.raise_()
        self.adjustSize()

        self.corner = corner
        self.margin = margin

        geo = self.geometry()
        # now the widget should have the correct size hints, let's move it to the
        # right place
        if corner == QtCore.Qt.TopLeftCorner:
            geo.moveTopLeft(parent_rect.topLeft() + QtCore.QPoint(margin, margin))
        elif corner == QtCore.Qt.TopRightCorner:
            geo.moveTopRight(parent_rect.topRight() + QtCore.QPoint(-margin, margin))
        elif corner == QtCore.Qt.BottomRightCorner:
            geo.moveBottomRight(
                parent_rect.bottomRight() + QtCore.QPoint(-margin, -margin)
            )
        else:
            geo.moveBottomLeft(
                parent_rect.bottomLeft() + QtCore.QPoint(margin, -margin)
            )

        self.setGeometry(geo)
        self.show()
        self.opacityAni.start()
