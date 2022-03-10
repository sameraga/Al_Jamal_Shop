#!/usr/bin/env python3


import locale
import math
import os
import sys
import tempfile
import time
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from jinja2 import Template
import xlwt
import notify2
import PyQt5.uic as uic
import hashlib
from QDate import QDate
import database

Form_Main, _ = uic.loadUiType('j_shop.ui')
PAGE_SIZE = 10
USER = ''
PASS = ''


class AppMainWindow(QtWidgets.QMainWindow, Form_Main):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Form_Main.__init__(self)
        self.setupUi(self)

        self.setup_login()

    def setup_login(self):
        self.menubar.setVisible(False)
        self.txt_username.setFocus()
        self.btn_in.clicked.connect(self.enter_app)
        self.btn_exit.clicked.connect(lambda: sys.exit(1))

    def enter_app(self):
        global PASS
        global USER

        PASS = hashlib.sha256(self.txt_password.text().encode()).digest()
        USER = self.txt_username.text()

        database.Database.open_database()
        p: dict = database.db.is_user(USER)
        if p and 'pass' in p and p['pass'] == PASS:
            # self.setup_controls()
            self.stackedWidget.setCurrentIndex(0)
        else:
            self.lbl_wrong.setText('* اسم المستخدم أو كلمة المرور غير صحيحة !!!')
            # self.lbl_wrong.setVisible(True)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    locale.setlocale(locale.LC_ALL, "en_US.utf8")

    mainWindow = AppMainWindow()
    mainWindow.showMaximized()
    mainWindow.setWindowIcon(QtGui.QIcon('icons/ph1.png'))
    exit_code = app.exec_()
