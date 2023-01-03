#!/usr/bin/env python3
import subprocess
import sys
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    from os import chdir
    chdir(sys._MEIPASS)

import glob
import locale
import math
import os
import tempfile
import time
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from jinja2 import Template
import xlwt
import PyQt5.uic as uic

import toaster_Notify
from QDate import QDate
import database
from dlg_choice_code import PrintDialog

Form_Main, _ = uic.loadUiType('j_shop.ui')
Form_BillSell, _ = uic.loadUiType('bill_sell.ui')
Form_BillBuy, _ = uic.loadUiType('bill_buy.ui')
PAGE_SIZE = 10
USER = ''
PASS = ''
PERMISSION = ''
SerialNumber = 'SerialNumberK2004N0103378'
DOLLAR = 0


class ReadOnlyDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        # print('createEditor event fired')
        return


class BillSell(QtWidgets.QDialog, Form_BillSell):
    def __init__(self, id):
        QtWidgets.QDialog.__init__(self)
        Form_BillSell.__init__(self)
        self.setupUi(self)

        self.validator_money = QtGui.QRegExpValidator(QtCore.QRegExp('^(([1-9]\d{0,2}(\d{3})*)|([1-9]\d*)|(0))(\.\d{1,2})?$'))

        self.ch = id
        self.b_id = id
        self.code = None
        self.setup_control()

    def setup_control(self):
        self.b_date.setDate(QDate.currentDate())
        self.discount_d.setValidator(self.validator_money)
        self.discount_t.setValidator(self.validator_money)
        self.paid_d.setValidator(self.validator_money)
        self.paid_t.setValidator(self.validator_money)

        self.ch_ispaid.stateChanged.connect(self.ch_ispaid_change)

        self.c_name.clear()
        self.c_name.addItems(database.db.query_csp("customer").values())
        self.c_name.currentTextChanged.connect(self.c_name_changed)

        self.bs_table: QtWidgets.QTableWidget
        delegate = ReadOnlyDelegate(self.bs_table)
        self.bs_table.setItemDelegateForColumn(3, delegate)
        self.bs_table.setItemDelegateForColumn(4, delegate)
        self.bs_table.setItemDelegateForColumn(6, delegate)
        self.bs_table.setItemDelegateForColumn(7, delegate)
        self.bs_table.setRowCount(1)
        self.bs_table.keyReleaseEvent = self.table_key_press_event

        self.discount_d.returnPressed.connect(lambda: self.discount_on_press("d"))
        self.discount_t.returnPressed.connect(lambda: self.discount_on_press("t"))
        self.paid_d.returnPressed.connect(lambda: self.paid_change("d"))
        self.paid_t.returnPressed.connect(lambda: self.paid_change("t"))
        self.fill_bill(self.b_id)

        self.btn_save.clicked.connect(self.save_bill)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_print_bill.clicked.connect(self.print_bill)

        self.btn_save.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)
        self.btn_print_bill.setAutoDefault(False)

    def ch_ispaid_change(self):
        if self.ch_ispaid.isChecked():
            self.paid_d.setEnabled(True)
            self.paid_t.setEnabled(True)
        else:
            self.paid_d.setEnabled(False)
            self.paid_t.setEnabled(False)

    def c_name_changed(self):
        if self.c_name.currentIndex() == 0:
            self.ch_ispaid.setEnabled(False)
        else:
            if self.ch == 0:
                self.ch_ispaid.setEnabled(True)
        self.c_phone.setText(database.db.get_phone_by_name('customer', self.c_name.currentText()))

    def fill_bill(self, id):
        if id == 0:
            self.b_id = database.db.get_next_id('bill_sell')
            self.code = int(self.b_id) + 10000
            global DOLLAR
            self.d_tr.setText(str(DOLLAR))
        else:
            bill = database.db.query_row('bill_sell', id)
            self.b_id = bill['id']
            self.code = bill['code']
            self.d_tr.setText(bill['dollar_tr'])
            self.bill_type.setCurrentIndex(int(bill['type']))
            self.b_date.setDate(QDate(bill['date']))
            self.c_name.setCurrentText(database.db.get_name_by_id('customer', bill['c_id']))
            self.total_d.setText(str(bill['total']))
            format_float = round(float(bill['total']) * float(bill['dollar_tr']), 2)
            self.total_t.setText(str(format_float))
            self.discount_d.setText(str(bill['discount']))
            format_float = round(float(bill['discount']) * float(bill['dollar_tr']), 2)
            self.discount_t.setText(str(format_float))
            format_float = round(float(bill['total']) - float(bill['discount']), 2)
            self.last_total_d.setText(str(format_float))
            format_float = round(float(self.total_t.text()) - float(self.discount_t.text()), 2)
            self.last_total_t.setText(str(format_float))
            if bill['ispaid'] == '1':
                self.ch_ispaid.setChecked(True)
                self.paid_d.setText(bill['paid_d'])
                self.paid_t.setText(bill['paid_t'])
            else:
                self.ch_ispaid.setChecked(False)
        self.bill_code.setText(str(self.code))
        orders = database.db.get_order_bill('sell_order_v', self.b_id)
        self.bs_table.setRowCount(len(orders) + 1)
        for row_idx, row in enumerate(orders):
            self.bs_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.bs_table.item(row_idx, 0).id = row['id']
            self.bs_table.item(row_idx, 0).pid = row['p_id']
            self.bs_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['name'])))
            self.bs_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(row['quantity'])))
            if self.bill_type.currentIndex() == 0:
                self.bs_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(row['sell_price'])))
            else:
                self.bs_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(row['sell_price_wh'])))
            format_float = round(float(self.bs_table.item(row_idx, 3).text()) * float(bill['dollar_tr']), 2)
            self.bs_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(format_float)))
            self.bs_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(str(row['discount'])))
            self.bs_table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(str(row['total'])))
            format_float = round(float(self.bs_table.item(row_idx, 6).text()) * float(bill['dollar_tr']), 2)
            self.bs_table.setItem(row_idx, 7, QtWidgets.QTableWidgetItem(str(format_float)))
            btn_delete = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('delete'), '')
            btn_delete.clicked.connect(lambda: self.delete_order(self.bs_table.currentRow()))
            self.bs_table.setCellWidget(row_idx, 8, btn_delete)

    def delete_order(self, current_row):
        self.bs_table.removeRow(current_row)
        self.calculate_total()

    def table_key_press_event(self, event: QtGui.QKeyEvent):
        self.bs_table: QtWidgets.QTableWidget
        if event.key() == QtCore.Qt.Key_Return:
            if self.bs_table.currentColumn() == 0 and self.bs_table.currentRow() + 1 == self.bs_table.rowCount():
                self.update_table(self.bs_table.currentRow())
                self.bs_table.setRowCount(self.bs_table.rowCount() + 1)
            elif self.bs_table.currentColumn() == 0 and self.bs_table.currentRow() + 1 != self.bs_table.rowCount():
                self.update_table(self.bs_table.currentRow())
            else:
                self.enter_event(self.bs_table.currentRow())

    def update_table(self, current_row):
        code = self.bs_table.item(current_row, 0).text()
        product = dict()
        product_result = database.db.get_product_like_code(code)
        if len(product_result) == 0:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'الرقم غير موجود\n أعد ادخال رقم صحيح')
            self.delete_order(current_row)
            return
        elif len(product_result) == 1:
            product = product_result[0]
        else:
            dlg = PrintDialog(code)
            dlg.exec()
            if dlg.result_value:
                product = dlg.result_value
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'الرقم غير موجود\n أعد ادخال رقم صحيح')
                self.delete_order(current_row)
                return

        if int(product['quantity']) >= 1:
            for idx in range(self.bs_table.rowCount() - 1):
                if self.bs_table.item(idx, 0).text() == product['code'] and current_row != idx:
                    new = int(self.bs_table.item(idx, 2).text()) + 1
                    self.bs_table.setItem(idx, 2, QtWidgets.QTableWidgetItem(str(new)))
                    total_d = new * float(self.bs_table.item(idx, 3).text())
                    total_d = round(total_d, 2)
                    self.bs_table.setItem(idx, 6, QtWidgets.QTableWidgetItem(str(total_d)))
                    total_t = new * float(self.bs_table.item(idx, 4).text())
                    total_t = round(total_t, 2)
                    self.bs_table.setItem(idx, 7, QtWidgets.QTableWidgetItem(str(total_t)))
                    self.bs_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(''))
                    self.delete_order(current_row)
                    return

            self.bs_table.item(current_row, 0).pid = product['id']
            self.bs_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(product['code']))
            self.bs_table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(product['name']))
            self.bs_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem('1'))
            if self.bill_type.currentIndex() == 0:
                self.bs_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(product['sell_price'])))
            else:
                self.bs_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(product['sell_price_wh'])))
            format_float = round(float(self.bs_table.item(current_row, 3).text()) * float(self.d_tr.text()), 2)
            self.bs_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem(str(format_float)))
            self.bs_table.setItem(current_row, 5, QtWidgets.QTableWidgetItem('0'))
            self.bs_table.setItem(current_row, 6, QtWidgets.QTableWidgetItem(self.bs_table.item(current_row, 3).text()))
            self.bs_table.setItem(current_row, 7, QtWidgets.QTableWidgetItem(str(format_float)))

            btn_delete = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('delete'), '')
            btn_delete.clicked.connect(lambda: self.delete_order(self.bs_table.currentRow()))
            self.bs_table.setCellWidget(current_row, 8, btn_delete)
            self.calculate_total()
        else:
            self.bs_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(''))
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'غير متوفر\n لقد انتهت كمية هذا المنتج بالفعل')
            self.delete_order(current_row)

    def enter_event(self, current_row):
        code = self.bs_table.item(current_row, 0).text()
        product = database.db.get_product_by_code(code)
        if self.bs_table.item(current_row, 5).text() == '':
            self.bs_table.setItem(current_row, 5, QtWidgets.QTableWidgetItem('0'))
        discount = float(self.bs_table.item(current_row, 5).text())
        if self.bs_table.item(current_row, 2).text() == '':
            self.bs_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem('1'))
        quantity = int(self.bs_table.item(current_row, 2).text())
        if quantity > int(product['quantity']):
            quantity = int(product['quantity'])
            self.bs_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem(product['quantity']))
            toaster_Notify.QToaster.show_message(parent=self,
                                                 message=f"غير متوفر\n لقد بقي من هذا المنتج {product['quantity']} قطعة فقط ")

        if discount > (float(product['price_range']) * float(self.d_tr.text()) * quantity):
            discount = float(product['price_range']) * float(self.d_tr.text()) * quantity
            self.bs_table.setItem(current_row, 5, QtWidgets.QTableWidgetItem(str(discount)))
        total = (quantity * float(self.bs_table.item(current_row, 3).text())) - (discount / float(self.d_tr.text()))
        total = round(total, 2)
        self.bs_table.setItem(current_row, 6, QtWidgets.QTableWidgetItem(str(total)))
        total = round(total * float(self.d_tr.text()), 2)
        self.bs_table.setItem(current_row, 7, QtWidgets.QTableWidgetItem(str(total)))
        self.calculate_total()

    def calculate_total(self):
        total = 0
        for i in range(0, self.bs_table.rowCount()):
            if self.bs_table.item(i, 5) is not None:
                total += float(self.bs_table.item(i, 6).text())
        total = round(total, 2)
        self.total_d.setText(str(total))
        ff = round(total - float(self.discount_d.text()), 2)
        self.last_total_d.setText(str(ff))
        ff = round(total * float(self.d_tr.text()), 2)
        self.total_t.setText(str(ff))
        ff = round(float(self.total_t.text()) - float(self.discount_t.text()), 2)
        self.last_total_t.setText(str(ff))

    def discount_on_press(self, x):
        global DOLLAR
        if x == "d":
            d_float = round(float(self.total_d.text()) - float(self.discount_d.text()), 2)
            self.last_total_d.setText(str(d_float))
            self.discount_t.setText(str(float(self.discount_d.text()) * DOLLAR))
            t_float = round(float(self.total_t.text()) - float(self.discount_t.text()), 2)
            self.last_total_t.setText(str(t_float))
        else:
            t_float = round(float(self.total_t.text()) - float(self.discount_t.text()), 2)
            self.last_total_t.setText(str(t_float))
            self.discount_d.setText(str(float(self.discount_t.text()) / DOLLAR))
            d_float = round(float(self.total_d.text()) - float(self.discount_d.text()), 2)
            self.last_total_d.setText(str(d_float))

    def paid_change(self, x):
        global DOLLAR
        if x == 'd':
            dd = float(self.last_total_d.text()) - float(self.paid_d.text())
            self.paid_t.setText(str(round(dd * DOLLAR, 2)))
        else:
            tt = float(self.last_total_t.text()) - float(self.paid_t.text())
            self.paid_d.setText(str(round(tt / DOLLAR, 2)))

    def save_bill(self):
        bill = dict()
        bill['id'] = self.b_id
        bill['code'] = self.bill_code.text()
        bill['dollar_tr'] = self.d_tr.text()
        bill['type'] = self.bill_type.currentIndex()
        bill['date'] = QDate.toString(self.b_date.date())
        bill['total'] = float(self.total_d.text())
        bill['discount'] = float(self.discount_d.text())
        bill['paid_d'] = float(self.paid_d.text())
        bill['paid_t'] = float(self.paid_t.text())
        bill['c_id'] = database.db.get_id_by_name('customer', self.c_name.currentText())
        if self.ch_ispaid.isChecked():
            bill['ispaid'] = 1
        else:
            bill['ispaid'] = 0
        orders = []
        for idx in range(self.bs_table.rowCount()):
            order = dict()
            order['b_id'] = self.b_id
            if self.bs_table.item(idx, 0) and self.bs_table.item(idx, 0).text():
                if hasattr(self.bs_table.item(idx, 0), 'id'):
                    order['id'] = self.bs_table.item(idx, 0).id
                    order['p_id'] = self.bs_table.item(idx, 0).pid
                else:
                    order['id'] = int(database.db.get_next_id('sell_order')) + idx
                    order['p_id'] = database.db.get_id_by_code('product', self.bs_table.item(idx, 0).text())
                if self.bs_table.item(idx, 2) and self.bs_table.item(idx, 2).text():
                    order['quantity'] = self.bs_table.item(idx, 2).text()

                if self.bs_table.item(idx, 5) and self.bs_table.item(idx, 5).text():
                    order['discount'] = self.bs_table.item(idx, 5).text()

                if self.bs_table.item(idx, 6) and self.bs_table.item(idx, 6).text():
                    order['total'] = self.bs_table.item(idx, 6).text()

                orders.append(order)

        if int(database.db.count_row("bill_sell", bill['code'])) == 0:
            database.db.insert_row("bill_sell", bill)
        else:
            database.db.update_row("bill_sell", bill)

        database.db.insert_table('sell_order', orders, self.b_id)
        self.accept()

    def print_bill(self):
        print('done')


class BillBuy(QtWidgets.QDialog, Form_BillBuy):
    def __init__(self, id):
        QtWidgets.QDialog.__init__(self)
        Form_BillBuy.__init__(self)
        self.setupUi(self)

        self.validator_money = QtGui.QRegExpValidator(QtCore.QRegExp('^(([1-9]\d{0,2}(\d{3})*)|([1-9]\d*)|(0))(\.\d{1,2})?$'))

        self.b_id = id
        self.code = None
        self.setup_control()

    def setup_control(self):
        self.b_date.setDate(QDate.currentDate())
        self.discount.setValidator(self.validator_money)

        self.s_name.clear()
        self.s_name.addItem('')
        self.s_name.addItems(database.db.query_csp("supplier").values())
        self.s_name.currentTextChanged.connect(self.s_name_changed)

        self.bb_table: QtWidgets.QTableWidget
        delegate = ReadOnlyDelegate(self.bb_table)
        self.bb_table.setItemDelegateForColumn(1, delegate)
        self.bb_table.setItemDelegateForColumn(4, delegate)
        self.bb_table.setRowCount(1)
        self.bb_table.keyReleaseEvent = self.table_key_press_event

        self.discount.returnPressed.connect(self.discount_on_press)
        self.fill_bill(self.b_id)

        self.btn_save.clicked.connect(self.save_bill)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_print_bill.clicked.connect(self.print_bill)

        self.btn_save.setAutoDefault(False)
        self.btn_cancel.setAutoDefault(False)
        self.btn_print_bill.setAutoDefault(False)

    def s_name_changed(self):
        if self.s_name.currentText() == '':
            self.s_phone.setText('-')
        else:
            self.s_phone.setText(database.db.get_phone_by_name('supplier', self.s_name.currentText()))

    def fill_bill(self, id):
        if id == 0:
            self.b_id = database.db.get_next_id('bill_buy')
            self.code = int(self.b_id) + 10000
        else:
            bill = database.db.query_row('bill_buy', id)
            self.b_id = bill['id']
            self.code = bill['code']
            self.bill_match_code.setText(bill['match_code'])
            self.b_date.setDate(QDate(bill['date']))
            self.s_name.setCurrentText(database.db.get_name_by_id('supplier', bill['s_id']))
            self.total.setText(str(bill['total']))
            self.discount.setText(str(bill['discount']))
            self.last_total.setText(str(float(bill['total']) - float(bill['discount'])))
            if bill['ispaid'] == '1':
                self.ch_ispaid.setChecked(True)
            else:
                self.ch_ispaid.setChecked(False)
        self.bill_code.setText(str(self.code))

        orders = database.db.get_order_bill('buy_order_v', self.b_id)
        self.bb_table.setRowCount(len(orders) + 1)
        for row_idx, row in enumerate(orders):
            self.bb_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.bb_table.item(row_idx, 0).id = row['id']
            self.bb_table.item(row_idx, 0).pid = row['p_id']
            self.bb_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['name'])))
            self.bb_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(row['quantity'])))
            self.bb_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(row['buy_price'])))
            self.bb_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(row['total'])))
            btn_delete = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('delete'), '')
            btn_delete.clicked.connect(lambda: self.delete_order(self.bb_table.currentRow()))
            self.bb_table.setCellWidget(row_idx, 5, btn_delete)

    def delete_order(self, current_row):
        self.bb_table.removeRow(current_row)
        self.calculate_total()

    def table_key_press_event(self, event: QtGui.QKeyEvent):
        self.bb_table: QtWidgets.QTableWidget
        if event.key() == QtCore.Qt.Key_Return:
            if self.bb_table.currentColumn() == 0 and self.bb_table.currentRow() + 1 == self.bb_table.rowCount():
                self.update_table(self.bb_table.currentRow())
                self.bb_table.setRowCount(self.bb_table.rowCount() + 1)
            elif self.bb_table.currentColumn() == 0 and self.bb_table.currentRow() + 1 != self.bb_table.rowCount():
                self.update_table(self.bb_table.currentRow())
            else:
                self.enter_event(self.bb_table.currentRow())

    def update_table(self, current_row):
        code = self.bb_table.item(current_row, 0).text()
        product = dict()
        product_result = database.db.get_product_like_code(code)
        if len(product_result) == 0:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'الرقم غير موجود\n أعد ادخال رقم صحيح')
            self.delete_order(current_row)
            return
        elif len(product_result) == 1:
            product = product_result[0]
        else:
            dlg = PrintDialog(code)
            dlg.exec()
            if dlg.result_value:
                product = dlg.result_value
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'الرقم غير موجود\n أعد ادخال رقم صحيح')
                self.delete_order(current_row)
                return

        for idx in range(self.bb_table.rowCount() - 1):
            if self.bb_table.item(idx, 0).text() == product['code'] and current_row != idx:
                new = int(self.bb_table.item(idx, 2).text()) + 1
                self.bb_table.setItem(idx, 2, QtWidgets.QTableWidgetItem(str(new)))
                total = new * float(self.bb_table.item(idx, 3).text())
                total = round(total, 2)
                self.bb_table.setItem(idx, 4, QtWidgets.QTableWidgetItem(str(total)))
                self.bb_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(''))
                self.delete_order(current_row)
                return

        self.bb_table.item(current_row, 0).pid = product['id']
        self.bb_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(product['code']))
        self.bb_table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(product['name']))
        self.bb_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem('1'))
        self.bb_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(product['buy_price'])))
        self.bb_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem(str(product['buy_price'])))

        btn_delete = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('delete'), '')
        btn_delete.clicked.connect(lambda: self.delete_order(self.bb_table.currentRow()))
        self.bb_table.setCellWidget(current_row, 5, btn_delete)
        self.calculate_total()

    def enter_event(self, current_row):
        if self.bb_table.item(current_row, 4).text() == '':
            self.bb_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem('0'))

        if self.bb_table.item(current_row, 2).text() == '':
            self.bb_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem('1'))
        quantity = int(self.bb_table.item(current_row, 2).text())

        total = quantity * float(self.bb_table.item(current_row, 3).text())
        self.bb_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem(str(total)))
        self.calculate_total()

    def calculate_total(self):
        total = 0
        for i in range(0, self.bb_table.rowCount()):
            if self.bb_table.item(i, 4) is not None:
                total += float(self.bb_table.item(i, 4).text())
        self.total.setText(str(total))
        self.last_total.setText(str(total - float(self.discount.text())))

    def discount_on_press(self):
        self.last_total.setText(str(float(self.total.text()) - float(self.discount.text())))

    def save_bill(self):
        bill = dict()
        bill['id'] = self.b_id
        bill['code'] = self.bill_code.text()
        bill['match_code'] = self.bill_match_code.text()
        bill['date'] = QDate.toString(self.b_date.date())
        bill['total'] = self.total.text()
        bill['discount'] = self.discount.text()
        if self.s_name.currentText() == '':
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'ادخال خاطئ\n يجب أن تدخل اسم المورد ')
            return
        bill['s_id'] = database.db.get_id_by_name('supplier', self.s_name.currentText())
        if self.ch_ispaid.isChecked():
            bill['ispaid'] = 1
        else:
            bill['ispaid'] = 0

        orders = []
        for idx in range(self.bb_table.rowCount()):
            order = dict()
            order['b_id'] = self.b_id
            if self.bb_table.item(idx, 0) and self.bb_table.item(idx, 0).text():
                if hasattr(self.bb_table.item(idx, 0), 'id'):
                    order['id'] = self.bb_table.item(idx, 0).id
                    order['p_id'] = self.bb_table.item(idx, 0).pid
                else:
                    order['id'] = int(database.db.get_next_id('buy_order')) + idx
                    order['p_id'] = database.db.get_id_by_code('product', self.bb_table.item(idx, 0).text())
                if self.bb_table.item(idx, 2) and self.bb_table.item(idx, 2).text():
                    order['quantity'] = self.bb_table.item(idx, 2).text()

                if self.bb_table.item(idx, 3) and self.bb_table.item(idx, 3).text():
                    order['price'] = self.bb_table.item(idx, 3).text()

                if self.bb_table.item(idx, 4) and self.bb_table.item(idx, 4).text():
                    order['total'] = self.bb_table.item(idx, 4).text()

                orders.append(order)
        if int(database.db.count_row("bill_buy", bill['code'])) == 0:
            database.db.insert_row("bill_buy", bill)
        else:
            database.db.update_row("bill_buy", bill)

        database.db.insert_table('buy_order', orders, self.b_id)
        self.accept()

    def print_bill(self):
        pass


class AppMainWindow(QtWidgets.QMainWindow, Form_Main):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Form_Main.__init__(self)
        self.setupUi(self)

        self.validator_code = QtGui.QRegExpValidator(QtCore.QRegExp('[\u0621-\u064A0-9a-zA-Z][0-9]*'))
        self.validator_int = QtGui.QRegExpValidator(QtCore.QRegExp('[0-9]+'))
        self.validator_money = QtGui.QRegExpValidator(QtCore.QRegExp('^(([1-9]\d{0,2}(\d{3})*)|([1-9]\d*)|(0))(\.\d{1,2})?$'))
        self.validator_phone = QtGui.QRegExpValidator(QtCore.QRegExp('\+[1-9]{1}[0-9]{11}'))

        self._typing_timer_p = QtCore.QTimer()
        self.product_id = 0
        self.product_co = 0
        self.page_size_product = PAGE_SIZE

        self._typing_timer_c = QtCore.QTimer()
        self.customer_id = 0
        self.customer_co = 0
        self.page_size_customer = PAGE_SIZE

        self.customers = None
        self.suppliers = None

        self._typing_timer_s = QtCore.QTimer()
        self.supplier_id = 0
        self.supplier_co = 0
        self.page_size_supplier = PAGE_SIZE

        self._typing_timer_bs = QtCore.QTimer()
        self.bill_sell_id = 0
        self.bill_sell_co = 0
        self.page_size_bill_sell = PAGE_SIZE

        self._typing_timer_bb = QtCore.QTimer()
        self.bill_buy_id = 0
        self.bill_buy_co = 0
        self.page_size_bill_buy = PAGE_SIZE

        self._typing_timer_fm = QtCore.QTimer()
        self.fm_id = 0
        self.page_size_fm = PAGE_SIZE

        self.setup_login()

    def setup_login(self):
        self.menubar.setVisible(False)
        self.stackedWidget.setCurrentIndex(1)
        self.txt_username.setFocus()
        self.btn_in.clicked.connect(self.enter_app)
        self.btn_exit.clicked.connect(lambda: sys.exit(1))

    def enter_app(self):
        global USER
        global PASS
        global PERMISSION
        if self.txt_password.text() != '' and self.txt_username.text() != '':
            database.Database.open_database()
            p = database.db.is_user(self.txt_username.text())
            if p is not None:
                if self.txt_password.text() == p['pass']:
                    PASS = self.txt_password.text()
                    USER = self.txt_username.text()
                    PERMISSION = p['permission']
                    self.setup_controls()
                    self.stackedWidget.setCurrentIndex(0)
                else:
                    self.lbl_wrong.setText('* كلمة المرور غير صحيحة !!!')
            else:
                self.lbl_wrong.setText('* اسم المستخدم غير صحيح !!!')
        else:
            self.lbl_wrong.setText('* يجب أن تدخل اسم المستخدم وكلمة المرور !!!')

    def change_pass_(self):
        self.stackedWidget.setCurrentIndex(2)
        self.menubar.setVisible(False)
        self.old_pass.setFocus()
        self.btn_save_pass.clicked.connect(self.save_new_pass)
        self.btn_cancel_pass.clicked.connect(
            lambda: self.stackedWidget.setCurrentIndex(0) or self.menubar.setVisible(True))

    def save_new_pass(self):
        global PASS
        if self.old_pass.text() == PASS:
            if self.new_pass.text() == self.new_pass_confirm.text():
                if self.new_pass.text() != '':
                    database.db.change_user_pass(USER, PASS)
                    self.stackedWidget.setCurrentIndex(0)
                    toaster_Notify.QToaster.show_message(parent=self,
                                                         message="تغيير كلمة المرور\nتم تغيير كلمة المرور بنجاح")
                else:
                    self.lbl_wrong.setText('* كلمة المرور الجديدة لا يمكن أن تكون فارغة !!!')
            else:
                self.lbl_wrong.setText('* كلمة المرور الجديدة غير متطابقة !!!')
        else:
            self.lbl_wrong_e.setText('* كلمة المرور القديمة غير صحيحة !!!')

    # setup controls
    def setup_controls(self):
        self.menubar.setVisible(True)
        self.tabWidget.tabBar().setVisible(False)
        self.tabWidget.setCurrentIndex(0)

        self.dollar_tr.setValidator(self.validator_money)
        self.ta_dt_d.setValidator(self.validator_money)
        self.ta_td_t.setValidator(self.validator_money)

        self.ta_dt_d.textChanged.connect(lambda: self.exchange_dollar('dollar'))
        self.ta_td_t.textChanged.connect(lambda: self.exchange_dollar('turky'))

        self.setup_box()

        self.btn_ta_dt.clicked.connect(lambda: self.exchange_dollar_turky('do_tu'))
        self.btn_ta_td.clicked.connect(lambda: self.exchange_dollar_turky('tu_do'))

        self.customers = database.db.query_csp("customer")
        self.suppliers = database.db.query_csp("supplier")

        # update tables
        self._typing_timer_p.setSingleShot(True)
        self._typing_timer_c.setSingleShot(True)
        self._typing_timer_s.setSingleShot(True)
        self._typing_timer_bs.setSingleShot(True)
        self._typing_timer_bb.setSingleShot(True)
        self._typing_timer_fm.setSingleShot(True)

        self.dollar_tr.textChanged.connect(self.dollar_change)
        self.change_pass.triggered.connect(self.change_pass_)
        self.exit.triggered.connect(lambda: sys.exit(1))

        self.update_notification()
        self.setup_controls_product()
        self.setup_controls_customer()
        self.setup_controls_supplier()
        self.setup_controls_bill_sell()
        self.setup_controls_bill_buy()
        self.setup_controls_fund_movement()
        self.calculate_main()

    def dollar_change(self):
        global DOLLAR
        if self.dollar_tr.text() == '':
            DOLLAR = 0
        else:
            DOLLAR = float(self.dollar_tr.text())
            self.calculate_main()

    def exchange_dollar(self, coin):
        global DOLLAR
        if DOLLAR == 0:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'أدخل سعر صرف الدولار')
            return
        if coin == 'dollar':
            if self.ta_dt_d.text() == '':
                d = 0
            else:
                d = float(self.ta_dt_d.text())
            if d == 0 or d > float(self.box_dolar.text()):
                self.btn_ta_dt.setEnabled(False)
                self.ta_dt_t.setText('0')
            elif d <= float(self.box_dolar.text()):
                self.btn_ta_dt.setEnabled(True)
                self.ta_dt_t.setText(str(round(d * DOLLAR, 2)))
        else:
            if self.ta_td_t.text() == '':
                d = 0
            else:
                d = float(self.ta_td_t.text())
            if d == 0 or d > float(self.box_turky.text()):
                self.btn_ta_td.setEnabled(False)
                self.ta_td_d.setText('0')
            elif d <= float(self.box_turky.text()):
                self.btn_ta_td.setEnabled(True)
                self.ta_td_d.setText(str(round(d / DOLLAR, 2)))

    def exchange_dollar_turky(self, to):
        if to == 'do_tu':
            database.db.exchange_dollar_turky("do_tu", float(self.ta_dt_d.text()), float(self.ta_dt_t.text()))
            self.ta_dt_d.setText('0')
            self.ta_dt_t.setText('0')
        else:
            database.db.exchange_dollar_turky("tu_do", float(self.ta_td_d.text()), float(self.ta_td_t.text()))
            self.ta_td_t.setText('0')
            self.ta_td_d.setText('0')
        self.setup_box()

    def setup_box(self):
        self.box_dolar.setText(database.db.get_box()['dollar'])
        self.box_turky.setText(database.db.get_box()['turky'])

    def change_page_size(self, table):
        if table == 'product':
            self.page_size_product = self.p_page_size.value()
            self.p_page_num.setRange(1, math.ceil(int(database.db.count_row("product", 1)) / self.page_size_product))
            self._typing_timer_p.start(1000)
        elif table == 'customer':
            self.page_size_customer = self.s_page_size_c.value()
            self.page_num_c.setRange(1, math.ceil(int(database.db.count_customer(1)) / self.page_size_c))
            self._typing_timer_c.start(1000)
        elif table == 'supplier':
            self.page_size_supplier = self.s_page_size.value()
            self.s_page_num.setRange(1, math.ceil(int(database.db.count_row("supplier", 1)) / self.page_size_s))
            self._typing_timer_s.start(1000)
        elif table == 'bill_sell':
            self.page_size_bill_sell = self.bs_page_size.value()
            self.bs_page_num.setRange(1,
                                      math.ceil(int(database.db.count_row("bill_sell", 1)) / self.page_size_bill_sell))
            self._typing_timer_bs.start(1000)
        elif table == 'bill_buy':
            self.page_size_bill_buy = self.bb_page_size.value()
            self.bb_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_buy", 1)) / self.page_size_bill_buy))
            self._typing_timer_bb.start(1000)
        elif table == 'fund_movement':
            self.page_size_fm = self.fm_page_size.value()
            self.fm_page_num.setRange(1, math.ceil(int(database.db.count_row("fund_movement", 1)) / self.page_size_fm))
            self._typing_timer_fm.start(1000)

    def check_date_from(self, x):
        if x == 'bell_sell':
            self._typing_timer_bs.start(1000)
            if self.ch_billsell_date_from.isChecked():
                self.billsell_date_from.setEnabled(True)
                self.billsell_date_from.dateChanged.connect(lambda: self._typing_timer_bs.start(1000))
                self.ch_billsell_date_to.setEnabled(True)
            else:
                self.billsell_date_from.setEnabled(False)
                self.billsell_date_from.setDate(QDate.currentDate())
                self.ch_billsell_date_to.setEnabled(False)
                self.billsell_date_to.setEnabled(False)
                self.billsell_date_to.setDate(QDate.currentDate())
                self.ch_billsell_date_to.setChecked(False)
        elif x == 'bell_buy':
            self._typing_timer_bb.start(1000)
            if self.ch_billbuy_date_from.isChecked():
                self.billbuy_date_from.setEnabled(True)
                self.billbuy_date_from.dateChanged.connect(lambda: self._typing_timer_bb.start(1000))
                self.ch_billbuy_date_to.setEnabled(True)
            else:
                self.billbuy_date_from.setEnabled(False)
                self.billbuy_date_from.setDate(QDate.currentDate())
                self.ch_billbuy_date_to.setEnabled(False)
                self.billbuy_date_to.setEnabled(False)
                self.billbuy_date_to.setDate(QDate.currentDate())
                self.ch_billbuy_date_to.setChecked(False)
        elif x == 'fund_movement':
            self._typing_timer_fm.start(1000)
            if self.ch_fm_date_from.isChecked():
                self.fm_date_from.setEnabled(True)
                self.fm_date_from.dateChanged.connect(lambda: self._typing_timer_fm.start(1000))
                self.ch_fm_date_to.setEnabled(True)
            else:
                self.fm_date_from.setEnabled(False)
                self.fm_date_from.setDate(QDate.currentDate())
                self.ch_fm_date_to.setEnabled(False)
                self.fm_date_to.setEnabled(False)
                self.fm_date_to.setDate(QDate.currentDate())
                self.ch_fm_date_to.setChecked(False)

    def check_date_to(self, x):
        if x == 'bell_sell':
            self._typing_timer_bs.start(1000)
            if self.ch_billsell_date_to.isChecked():
                self.billsell_date_to.setEnabled(True)
                self.billsell_date_to.dateChanged.connect(lambda: self._typing_timer_bs.start(1000))
            else:
                self.billsell_date_to.setEnabled(False)
                self.billsell_date_to.setDate(QDate.currentDate())
        elif x == 'bell_buy':
            self._typing_timer_bb.start(1000)
            if self.ch_billbuy_date_to.isChecked():
                self.billbuy_date_to.setEnabled(True)
                self.billbuy_date_to.dateChanged.connect(lambda: self._typing_timer_bb.start(1000))
            else:
                self.billbuy_date_to.setEnabled(False)
                self.billbuy_date_to.setDate(QDate.currentDate())
        elif x == 'fund_movement':
            self._typing_timer_fm.start(1000)
            if self.ch_fm_date_to.isChecked():
                self.fm_date_to.setEnabled(True)
                self.fm_date_to.dateChanged.connect(lambda: self._typing_timer_fm.start(1000))
            else:
                self.fm_date_to.setEnabled(False)
                self.fm_date_to.setDate(QDate.currentDate())

    ####################################################################

    # product methods
    def setup_controls_product(self):
        self.p_code.setValidator(self.validator_code)
        self.p_code_search.setValidator(self.validator_code)
        self.p_quantity.setValidator(self.validator_int)
        self.p_less_quantity.setValidator(self.validator_int)
        self.p_buy_price.setValidator(self.validator_money)
        self.p_sell_price.setValidator(self.validator_money)
        self.p_sell_price_wh.setValidator(self.validator_money)
        self.p_price_range.setValidator(self.validator_money)

        self.p_class.currentTextChanged.connect(lambda: self.p_class_changed(self.p_class))
        self.p_class_search.currentTextChanged.connect(lambda: self.p_class_changed(self.p_class_search))
        self._typing_timer_p.timeout.connect(self.update_product_table)

        # table
        self.p_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.p_table.doubleClicked.connect(lambda mi: self.fill_product_info(self.p_table.item(mi.row(), 0).id))
        self.p_table.clicked.connect(lambda mi: self.one_click_p(self.p_table.item(mi.row(), 0).id))
        self.p_page_num.setRange(1, math.ceil(int(database.db.count_row("product", 1)) / self.page_size_product))

        # search
        self.p_code_search.textChanged.connect(lambda text: self._typing_timer_p.start(1000))
        self.p_name_search.textChanged.connect(lambda text: self._typing_timer_p.start(1000))
        self.p_class_search.currentTextChanged.connect(lambda text: self._typing_timer_p.start(1000))
        self.p_type_search.currentTextChanged.connect(lambda text: self._typing_timer_p.start(1000))

        self.p_page_num.valueChanged.connect(lambda text: self._typing_timer_p.start(1000))
        self.p_page_size.valueChanged.connect(lambda: self.change_page_size('product'))

        # btn
        self.btn_add_product.clicked.connect(self.create_new_product)
        self.btn_edit_product.clicked.connect(self.update_product)
        self.btn_delete_product.clicked.connect(self.delete_product)
        self.btn_clear_product.clicked.connect(self.clear_product_inputs)

        # print and to exel
        self.btn_print_table_p.clicked.connect(self.print_table_product)
        self.btn_to_exel_p.clicked.connect(lambda: self.to_excel(self.p_table))

        # pages
        self.p_post.clicked.connect(lambda: self.p_page_num.setValue(self.p_page_num.value() + 1))
        self.p_previous.clicked.connect(lambda: self.p_page_num.setValue(self.p_page_num.value() - 1))
        self.p_last.clicked.connect(lambda: self.p_page_num.setValue(
            math.ceil(int(database.db.count_row("product", 1)) / self.page_size_product)))
        self.p_first.clicked.connect(lambda: self.p_page_num.setValue(1))

        self.btn_edit_product.setEnabled(False)
        self.btn_delete_product.setEnabled(False)

        self.update_product_table()
        self.clear_product_inputs()

    def p_class_changed(self, combo: QtWidgets.QComboBox):
        if combo.objectName() == 'p_class':
            if combo.currentIndex() == 5:
                self.p_type.addItem("نسائي")
                self.p_type.setCurrentIndex(3)
                self.p_type.setEnabled(False)
            else:
                self.p_type.setEnabled(True)
                self.p_type.removeItem(3)
                self.p_type.setCurrentIndex(0)
        else:
            if combo.currentIndex() == 5:
                self.p_type_search.addItem("نسائي")
                self.p_type_search.setCurrentIndex(3)
                self.p_type_search.setEnabled(False)
            else:
                self.p_type_search.setEnabled(True)
                self.p_type_search.removeItem(3)
                self.p_type_search.setCurrentIndex(0)

    def one_click_p(self, id):
        self.product_id = id
        self.btn_delete_product.setEnabled(True)

    def save_product_info(self):
        product = dict()
        product['code'] = self.p_code.text()
        product['name'] = self.p_name.text()
        product['class'] = self.p_class.currentText()
        product['type'] = self.p_type.currentText()
        product['source'] = self.p_source.text()
        product['quantity'] = self.p_quantity.text()
        product['less_quantity'] = self.p_less_quantity.text()
        product['buy_price'] = self.p_buy_price.text()
        product['sell_price'] = self.p_sell_price.text()
        product['sell_price_wh'] = self.p_sell_price_wh.text()
        product['price_range'] = self.p_price_range.text()

        return product

    def create_new_product(self):
        product = self.save_product_info()
        if product['code'] and product['name']:
            if product['buy_price'] and product['sell_price'] and product['sell_price_wh'] and product['price_range']:
                if int(database.db.count_row("product", product['code'])) == 0:
                    database.db.insert_row("product", product)
                    toaster_Notify.QToaster.show_message(parent=self,
                                                         message=f"إضافة مادة\nتم إضافة المادة {product['name']} بنجاح")
                    self.update_product_table()
                    self.clear_product_inputs()
                else:
                    QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب ادخال كافة الأسعار')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المادة')

    def update_product(self):
        product = self.save_product_info()
        product['id'] = self.product_id
        if product['code'] and product['name']:
            if product['buy_price'] and product['sell_price'] and product['sell_price_wh'] and product['price_range']:
                if product['code'] == self.product_co:
                    database.db.update_row("product", product)
                    self.update_product_table()
                    self.clear_product_inputs()
                    toaster_Notify.QToaster.show_message(parent=self,
                                                         message=f"تعديل مادة\nتم تعديل المادة {product['name']} بنجاح")
                elif int(database.db.count_row("product", product['code'])) == 0:
                    database.db.update_row("product", product)
                    self.update_product_table()
                    self.clear_product_inputs()
                    toaster_Notify.QToaster.show_message(parent=self,
                                                         message=f"تعديل مادة\nتم تعديل المادة {product['name']} بنجاح")
                else:
                    QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب ادخال كافة الأسعار')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المادة')

    def delete_product(self):
        product = self.save_product_info()
        msg = QtWidgets.QMessageBox()
        button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {product['name']} ؟ ",
                                    msg.Yes | msg.No,
                                    msg.No)
        if button_reply == msg.Yes:
            database.db.delete_row("product", self.product_id)
            self.update_product_table()
            self.clear_product_inputs()
            toaster_Notify.QToaster.show_message(parent=self,
                                                 message=f"حذف مادة\nتم حذف المادة{product['name']} بنجاح")
        self.btn_delete_product.setEnabled(False)

    def search_product_save(self):
        fil = {}
        if self.p_code_search.text():
            fil['code'] = self.p_code_search.text()
        if self.p_name_search.text():
            fil['name'] = self.p_name_search.text()
        if self.p_class_search.currentText():
            fil['class'] = self.p_class_search.currentText()
        if self.p_type_search.currentText():
            fil['type'] = self.p_type_search.currentText()

        return fil

    def update_product_table(self):
        fil = self.search_product_save()
        rows = database.db.query_all_product(fil, self.page_size_product * (self.p_page_num.value() - 1),
                                             self.page_size_product)
        self.p_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.p_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_product * (self.p_page_num.value() - 1)))))
            self.p_table.item(row_idx, 0).id = row['id']
            self.p_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.p_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['name']))
            self.p_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(row['class']))
            self.p_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(row['type']))
            self.p_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(row['quantity']))
            self.p_table.item(row_idx, 5).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(row['buy_price']))
            self.p_table.item(row_idx, 6).setTextAlignment(QtCore.Qt.AlignCenter)
            total_buy = float(row['buy_price']) * float(row['quantity'])
            self.p_table.setItem(row_idx, 7, QtWidgets.QTableWidgetItem(str(total_buy)))
            self.p_table.item(row_idx, 7).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 8, QtWidgets.QTableWidgetItem(row['sell_price']))
            self.p_table.item(row_idx, 8).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 9, QtWidgets.QTableWidgetItem(row['source']))
            self.p_table.item(row_idx, 9).setTextAlignment(QtCore.Qt.AlignCenter)
        self.p_table.resizeColumnsToContents()
        self.update_notification()

    def clear_product_inputs(self):
        self.product_id = 0
        self.product_co = 0

        self.p_code.clear()
        self.p_code.setFocus()
        self.p_name.clear()
        self.p_class.setCurrentIndex(0)
        self.p_type.setCurrentIndex(0)
        self.p_source.clear()
        self.p_quantity.setText('0')
        self.p_less_quantity.setText('0')
        self.p_buy_price.setText('0')
        self.p_sell_price.setText('0')
        self.p_sell_price_wh.setText('0')
        self.p_price_range.setText('0')

        self.btn_edit_product.setEnabled(False)
        self.btn_delete_product.setEnabled(False)
        self.btn_add_product.setEnabled(True)

    def fill_product_info(self, id):
        self.btn_edit_product.setEnabled(True)
        self.btn_delete_product.setEnabled(True)
        self.btn_add_product.setEnabled(False)
        self.product_id = id
        product = database.db.query_row("product", id)
        if product:
            self.product_co = product['code']
            self.p_code.setText(product['code'])
            self.p_name.setText(product['name'])
            self.p_class.setCurrentText(product['class'])
            self.p_type.setCurrentText(product['type'])
            self.p_source.setText(product['source'])
            self.p_quantity.setText(product['quantity'])
            self.p_less_quantity.setText(product['less_quantity'])
            self.p_buy_price.setText(product['buy_price'])
            self.p_sell_price.setText(product['sell_price'])
            self.p_sell_price_wh.setText(product['sell_price_wh'])
            self.p_price_range.setText(product['price_range'])

    def print_table_product(self):
        fil = self.search_product_save()
        products = database.db.query_all_product(fil, 0, database.db.count_row("product", 1))
        with open('./html/product_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, product in enumerate(products):
                product['idx'] = idx + 1

            html = template.render(products=products, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    ####################################################################

    # customer methods
    def setup_controls_customer(self):
        self.c_code.setValidator(self.validator_code)
        self.c_code_search.setValidator(self.validator_code)
        self.c_balance.setValidator(self.validator_money)
        self.c_phone.setValidator(self.validator_phone)

        self._typing_timer_c.timeout.connect(self.update_customer_table)

        # table
        self.c_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.c_table.doubleClicked.connect(lambda mi: self.fill_customer_info(self.c_table.item(mi.row(), 0).id))
        self.c_table.clicked.connect(lambda mi: self.one_click_c(self.c_table.item(mi.row(), 0).id))
        self.c_page_num.setRange(1, math.ceil(int(database.db.count_row("customer", 1)) / self.page_size_customer))

        # search
        self.c_code_search.textChanged.connect(lambda text: self._typing_timer_c.start(1000))
        self.c_name_search.textChanged.connect(lambda text: self._typing_timer_c.start(1000))
        self.c_page_num.valueChanged.connect(lambda text: self._typing_timer_c.start(1000))
        self.c_page_size.valueChanged.connect(lambda: self.change_page_size('customer'))

        # btn
        self.btn_add_customer.clicked.connect(self.create_new_customer)
        self.btn_edit_customer.clicked.connect(self.update_customer)
        self.btn_delete_customer.clicked.connect(self.delete_customer)
        self.btn_clear_customer.clicked.connect(self.clear_customer_inputs)

        # print and to exel
        self.btn_print_table_c.clicked.connect(self.print_table_customer)
        self.btn_to_exel_c.clicked.connect(lambda: self.to_excel(self.c_table))

        # pages
        self.c_post.clicked.connect(lambda: self.c_page_num.setValue(self.c_page_num.value() + 1))
        self.c_previous.clicked.connect(lambda: self.c_page_num.setValue(self.c_page_num.value() - 1))
        self.c_last.clicked.connect(lambda: self.c_page_num.setValue(
            math.ceil(int(database.db.count_row("customer", 1)) / self.page_size_customer)))
        self.c_first.clicked.connect(lambda: self.c_page_num.setValue(1))

        self.btn_edit_customer.setEnabled(False)
        self.btn_delete_customer.setEnabled(False)

        self.update_customer_table()
        self.clear_customer_inputs()

    def one_click_c(self, id):
        self.customer_id = id
        self.btn_delete_customer.setEnabled(True)

    def save_customer_info(self):
        customer = dict()
        customer['code'] = self.c_code.text()
        customer['name'] = self.c_name.text()
        customer['phone'] = self.c_phone.text()
        customer['balance'] = self.c_balance.text()
        customer['range_balance'] = self.c_balance_range.text()
        customer['note'] = self.c_note.toPlainText()

        return customer

    def create_new_customer(self):
        customer = self.save_customer_info()
        if customer['code'] and customer['name']:
            if int(database.db.count_row("customer", customer['code'])) == 0:
                database.db.insert_row("customer", customer)
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"إضافة زبون\nتم إضافة الزبون {customer['name']} بنجاح")
                self.customers = database.db.query_csp("customer")
                self.update_customer_table()
                self.clear_customer_inputs()
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم الزبون')

    def update_customer(self):
        customer = self.save_customer_info()
        customer['id'] = self.customer_id
        if customer['code'] and customer['name']:
            if customer['code'] == self.customer_co:
                database.db.update_row("customer", customer)
                self.update_customer_table()
                self.clear_customer_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل زبون\nتم تعديل الزبون {customer['name']} بنجاح")
            elif int(database.db.count_row("customer", customer['code'])) == 0:
                database.db.update_row("customer", customer)
                self.update_customer_table()
                self.clear_customer_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل زبون\nتم تعديل الزبون {customer['name']} بنجاح")
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم الزبون')

    def delete_customer(self):
        customer = self.save_customer_info()
        msg = QtWidgets.QMessageBox()
        button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {customer['name']} ؟ ",
                                    msg.Yes | msg.No,
                                    msg.No)
        if button_reply == msg.Yes:
            database.db.delete_row("customer", self.customer_id)
            self.customers = database.db.query_csp("customer")
            self.update_customer_table()
            self.clear_customer_inputs()
            toaster_Notify.QToaster.show_message(parent=self,
                                                 message=f"حذف زبون\nتم حذف الزبون{customer['name']} بنجاح")
        self.btn_delete_customer.setEnabled(False)

    def search_customer_save(self):
        fil = {}
        if self.c_code_search.text():
            fil['code'] = self.c_code_search.text()
        if self.c_name_search.text():
            fil['name'] = self.c_name_search.text()

        return fil

    def update_customer_table(self):
        fil = self.search_customer_save()
        rows = database.db.query_all_cs('customer', fil, self.page_size_customer * (self.c_page_num.value() - 1),
                                        self.page_size_customer)
        self.c_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.c_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_customer * (self.c_page_num.value() - 1)))))
            self.c_table.item(row_idx, 0).id = row['id']
            self.c_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.c_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.c_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            self.c_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['name']))
            self.c_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            self.c_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(row['phone']))
            self.c_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            self.c_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(row['balance'])))
            self.c_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
        self.c_table.resizeColumnsToContents()

    def clear_customer_inputs(self):
        self.customer_id = 0
        self.customer_co = 0

        self.c_code.clear()
        self.c_code.setFocus()
        self.c_name.clear()
        self.c_phone.clear()
        self.c_balance.setText('0')
        self.c_balance_range.setText('100')
        self.c_note.clear()

        self.btn_edit_customer.setEnabled(False)
        self.btn_delete_customer.setEnabled(False)
        self.btn_add_customer.setEnabled(True)

    def fill_customer_info(self, id):
        if id == '1':
            self.clear_customer_inputs()
            return
        self.btn_edit_customer.setEnabled(True)
        self.btn_delete_customer.setEnabled(True)
        self.btn_add_customer.setEnabled(False)
        self.customer_id = id
        customer = database.db.query_row("customer", id)
        if customer:
            self.customer_co = customer['code']
            self.c_code.setText(customer['code'])
            self.c_name.setText(customer['name'])
            self.c_phone.setText(customer['phone'])
            self.c_balance.setText(str(customer['balance']))
            self.c_balance_range.setText(str(customer['range_balance']))
            self.c_note.setText(customer['note'])

    def print_table_customer(self):
        fil = self.search_customer_save()
        customer = database.db.query_all_cs('customer', fil, 0, database.db.count_row("customer", 1))
        with open('./html/customer_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, customer in enumerate(customer):
                customer['idx'] = idx + 1

            html = template.render(customer=customer, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    ####################################################################

    # suppliers methods
    def setup_controls_supplier(self):
        self.s_code.setValidator(self.validator_code)
        self.s_code_search.setValidator(self.validator_code)
        self.s_balance.setValidator(self.validator_money)
        self.s_phone.setValidator(self.validator_phone)

        self._typing_timer_s.timeout.connect(self.update_supplier_table)

        # table
        self.s_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.s_table.doubleClicked.connect(lambda mi: self.fill_supplier_info(self.s_table.item(mi.row(), 0).id))
        self.s_table.clicked.connect(lambda mi: self.one_click_s(self.s_table.item(mi.row(), 0).id))
        self.s_page_num.setRange(1, math.ceil(int(database.db.count_row("supplier", 1)) / self.page_size_supplier))

        # search
        self.s_code_search.textChanged.connect(lambda text: self._typing_timer_s.start(1000))
        self.s_name_search.textChanged.connect(lambda text: self._typing_timer_s.start(1000))

        self.s_page_num.valueChanged.connect(lambda text: self._typing_timer_s.start(1000))
        self.s_page_size.valueChanged.connect(lambda: self.change_page_size('supplier'))

        # btn
        self.btn_add_supplier.clicked.connect(self.create_new_supplier)
        self.btn_edit_supplier.clicked.connect(self.update_supplier)
        self.btn_delete_supplier.clicked.connect(self.delete_supplier)
        self.btn_clear_supplier.clicked.connect(self.clear_supplier_inputs)

        # print and to exel
        self.btn_print_table_s.clicked.connect(self.print_table_supplier)
        self.btn_to_exel_s.clicked.connect(lambda: self.to_excel(self.s_table))

        # pages
        self.s_post.clicked.connect(lambda: self.s_page_num.setValue(self.s_page_num.value() + 1))
        self.s_previous.clicked.connect(lambda: self.s_page_num.setValue(self.s_page_num.value() - 1))
        self.s_last.clicked.connect(lambda: self.s_page_num.setValue(
            math.ceil(int(database.db.count_row("supplier", 1)) / self.page_size_supplier)))
        self.s_first.clicked.connect(lambda: self.s_page_num.setValue(1))

        self.btn_edit_supplier.setEnabled(False)
        self.btn_delete_supplier.setEnabled(False)

        self.update_supplier_table()
        self.clear_supplier_inputs()

    def one_click_s(self, id):
        self.supplier_id = id
        self.btn_delete_supplier.setEnabled(True)

    def save_supplier_info(self):
        supplier = dict()
        supplier['code'] = self.s_code.text()
        supplier['name'] = self.s_name.text()
        supplier['phone'] = self.s_phone.text()
        supplier['address'] = self.s_address.toPlainText()
        supplier['balance'] = self.s_balance.text()
        supplier['range_balance'] = self.s_balance_range.text()
        supplier['note'] = self.s_note.toPlainText()

        return supplier

    def create_new_supplier(self):
        supplier = self.save_supplier_info()
        if supplier['code'] and supplier['name']:
            if int(database.db.count_row("supplier", supplier['code'])) == 0:
                database.db.insert_row("supplier", supplier)
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"إضافة مورد\nتم إضافة المورد {supplier['name']} بنجاح")
                self.suppliers = database.db.query_csp("supplier")
                self.update_supplier_table()
                self.clear_supplier_inputs()
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المورد')

    def update_supplier(self):
        supplier = self.save_supplier_info()
        supplier['id'] = self.supplier_id
        if supplier['code'] and supplier['name']:
            if supplier['code'] == self.supplier_co:
                database.db.update_row("supplier", supplier)
                self.update_supplier_table()
                self.clear_supplier_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مورد\nتم تعديل المورد {supplier['name']} بنجاح")
            elif int(database.db.count_row("supplier", supplier['code'])) == 0:
                database.db.update_row("supplier", supplier)
                self.update_supplier_table()
                self.clear_supplier_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مورد\nتم تعديل المورد {supplier['name']} بنجاح")
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المورد')

    def delete_supplier(self):
        supplier = self.save_supplier_info()
        msg = QtWidgets.QMessageBox()
        button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {supplier['name']} ؟ ",
                                    msg.Yes | msg.No,
                                    msg.No)
        if button_reply == msg.Yes:
            database.db.delete_row("supplier", self.supplier_id)
            self.suppliers = database.db.query_csp("supplier")
            self.update_supplier_table()
            self.clear_supplier_inputs()
            toaster_Notify.QToaster.show_message(parent=self,
                                                 message=f"حذف مورد\nتم حذف المورد{supplier['name']} بنجاح")
        self.btn_delete_supplier.setEnabled(False)

    def search_supplier_save(self):
        fil = {}
        if self.s_code_search.text():
            fil['code'] = self.s_code_search.text()
        if self.s_name_search.text():
            fil['name'] = self.s_name_search.text()

        return fil

    def update_supplier_table(self):
        fil = self.search_supplier_save()
        rows = database.db.query_all_cs('supplier', fil, self.page_size_supplier * (self.s_page_num.value() - 1),
                                        self.page_size_supplier)
        self.s_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.s_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_supplier * (self.s_page_num.value() - 1)))))
            self.s_table.item(row_idx, 0).id = row['id']
            self.s_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.s_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.s_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            self.s_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['name']))
            self.s_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            self.s_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(row['phone']))
            self.s_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            self.s_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(row['balance'])))
            self.s_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
        self.s_table.resizeColumnsToContents()

    def clear_supplier_inputs(self):
        self.supplier_id = 0
        self.supplier_co = 0

        self.s_code.clear()
        self.s_code.setFocus()
        self.s_name.clear()
        self.s_phone.clear()
        self.s_address.clear()
        self.s_balance.setText('0')
        self.s_balance_range.setText('100')
        self.s_note.clear()

        self.btn_edit_supplier.setEnabled(False)
        self.btn_delete_supplier.setEnabled(False)
        self.btn_add_supplier.setEnabled(True)

    def fill_supplier_info(self, id):
        self.btn_edit_supplier.setEnabled(True)
        self.btn_delete_supplier.setEnabled(True)
        self.btn_add_supplier.setEnabled(False)
        self.supplier_id = id
        supplier = database.db.query_row("supplier", id)
        if supplier:
            self.supplier_co = supplier['code']
            self.s_code.setText(supplier['code'])
            self.s_name.setText(supplier['name'])
            self.s_phone.setText(supplier['phone'])
            self.s_address.setText(supplier['address'])
            self.s_balance.setText(str(supplier['balance']))
            self.s_balance_range.setText(str(supplier['range_balance']))
            self.s_note.setText(supplier['note'])

    def print_table_supplier(self):
        fil = self.search_supplier_save()
        suppliers = database.db.query_all_cs('supplier', fil, 0, database.db.count_row("supplier", 1))
        with open('./html/supplier_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, supplier in enumerate(suppliers):
                supplier['idx'] = idx + 1

            html = template.render(suppliers=suppliers, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    ####################################################################

    # bill sell methods
    def setup_controls_bill_sell(self):
        self.billsell_code.setValidator(self.validator_code)
        self._typing_timer_bs.timeout.connect(self.update_bill_sell_table)

        self.billsell_cname.addItem('')
        self.billsell_cname.addItems(self.customers.values())

        self.bs_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.bs_table.doubleClicked.connect(lambda mi: self.double_click_bs(self.bs_table.item(mi.row(), 0).id))
        self.bs_table.clicked.connect(lambda mi: self.one_click_bs(self.bs_table.item(mi.row(), 0).id))
        self.bs_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_sell", 1)) / self.page_size_bill_sell))

        self.billsell_code.textChanged.connect(lambda text: self._typing_timer_bs.start(1000))
        self.billsell_cname.currentTextChanged.connect(lambda text: self._typing_timer_bs.start(1000))

        self.ch_billsell_date_from.toggled.connect(lambda: self.check_date_from('bell_sell'))
        self.ch_billsell_date_to.toggled.connect(lambda: self.check_date_to('bell_sell'))

        self.bs_page_num.valueChanged.connect(lambda text: self._typing_timer_bs.start(1000))
        self.bs_page_size.valueChanged.connect(lambda: self.change_page_size('bell_sell'))

        # print and to exel
        self.btn_print_table_bs.clicked.connect(self.print_table_bill_sell)
        self.btn_to_exel_bs.clicked.connect(lambda: self.to_excel(self.bs_table))

        # pages
        self.bs_post.clicked.connect(lambda: self.bs_page_num.setValue(self.bs_page_num.value() + 1))
        self.bs_previous.clicked.connect(lambda: self.bs_page_num.setValue(self.bs_page_num.value() - 1))
        self.bs_last.clicked.connect(lambda: self.bs_page_num.setValue(
            math.ceil(int(database.db.count_row("bell_sell", 1)) / self.page_size_bell_sell)))
        self.bs_first.clicked.connect(lambda: self.bs_page_num.setValue(1))

        self.btn_add_billsell.clicked.connect(lambda: self.open_bill_sell(0))
        self.btn_edit_billsell.clicked.connect(lambda: self.open_bill_sell(self.bill_sell_id))

        self.billsell_date_from.setSpecialValueText(' ')
        self.billsell_date_to.setSpecialValueText(' ')

        self.billsell_date_from.setDate(QDate.currentDate())
        self.billsell_date_to.setDate(QDate.currentDate())

        self.btn_edit_billsell.setEnabled(False)

        self.billsell_date_from.setEnabled(False)
        self.ch_billsell_date_to.setEnabled(False)
        self.billsell_date_to.setEnabled(False)

        self.update_bill_sell_table()

    def one_click_bs(self, id):
        self.bill_sell_id = id
        self.btn_edit_billsell.setEnabled(True)

    def double_click_bs(self, id):
        self.bill_sell_id = id
        self.open_bill_sell(id)

    def open_bill_sell(self, id):
        global DOLLAR
        if DOLLAR == 0:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'أدخل سعر تصريف الدولار بالليرة التركية من الصفحة الرئيسية')
            return
        sb = BillSell(id)
        sb.setWindowIcon(QtGui.QIcon('emp.png'))
        sb.exec()
        self.btn_edit_billsell.setEnabled(False)
        self.update_bill_sell_table()
        self.update_product_table()
        self.update_customer_table()
        self.calculate_main()

    def calculate_main(self):
        global DOLLAR
        self.month_sales: QtWidgets.QLCDNumber
        self.month_sales.display(database.db.get_sales(30))
        self.capital.display(database.db.get_capital(True, DOLLAR))
        if database.db.get_earnings(30) == '':
            self.month_earnings.display(0)
        else:
            self.month_earnings.display(database.db.get_earnings(30))
        if database.db.get_purchases(30) == '':
            self.month_purchases.display(0)
        else:
            self.month_purchases.display(database.db.get_purchases(30))
        self.setup_box()

    def search_bill_sell_save(self):
        fil = {}
        if self.billsell_code.text():
            fil['code'] = self.billsell_code.text()
        if self.billsell_cname.currentText() != '':
            fil['c_id'] = [k for k, v in self.customers.items() if v == self.billsell_cname.currentText()][0]
        if self.ch_billsell_date_from.isChecked():
            fil['date_from'] = QDate.toString(self.billsell_date_from.date())
            if self.ch_billsell_date_to.isChecked():
                fil['date_to'] = QDate.toString(self.billsell_date_to.date())

        return fil

    def update_bill_sell_table(self):
        fil = self.search_bill_sell_save()
        rows = database.db.query_all_bill("bill_sell", fil, self.page_size_bill_sell * (self.bs_page_num.value() - 1),
                                          self.page_size_bill_sell)
        self.bs_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.bs_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_bill_sell * (self.bs_page_num.value() - 1)))))
            self.bs_table.item(row_idx, 0).id = row['id']
            self.bs_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.bs_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.bs_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            row['c_id'] = self.customers[row['c_id']]
            self.bs_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['c_id']))
            self.bs_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            total = str(float(row['total']) - float(row['discount']))
            self.bs_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(total))
            self.bs_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            if row['ispaid'] == '1':
                row['ispaid'] = 'مدفوعة'
            else:
                row['ispaid'] = 'غير مدفوعة'
            self.bs_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(row['ispaid']))
            self.bs_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
            self.bs_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(row['date']))
            self.bs_table.item(row_idx, 5).setTextAlignment(QtCore.Qt.AlignCenter)
        self.bs_table.resizeColumnsToContents()
        self.update_notification()

    def print_table_bill_sell(self):
        fil = self.search_bill_sell_save()
        bills = database.db.query_all_bill("bill_sell", fil, 0, database.db.count_row("bill_sell", 1))
        with open('./html/bill_sell_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, bill in enumerate(bills):
                bill['idx'] = idx + 1
                bill['c_id'] = self.customers[bill['c_id']]
                bill['total'] = str(float(bill['total']) - float(bill['discount']))
                if bill['ispaid'] == '1':
                    bill['ispaid'] = 'مدفوعة'
                else:
                    bill['ispaid'] = 'غير مدفوعة'
            html = template.render(bills=bills, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    ####################################################################

    # bill buy methods
    def setup_controls_bill_buy(self):
        self.billbuy_code.setValidator(self.validator_code)
        self._typing_timer_bb.timeout.connect(self.update_bill_buy_table)

        self.billbuy_sname.addItem('')
        self.billbuy_sname.addItems(self.suppliers.values())

        self.bb_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.bb_table.doubleClicked.connect(lambda mi: self.double_click(self.bb_table.item(mi.row(), 0).id))
        self.bb_table.clicked.connect(lambda mi: self.one_click_bb(self.bb_table.item(mi.row(), 0).id))
        self.bb_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_buy", 1)) / self.page_size_bill_buy))

        self.billbuy_code.textChanged.connect(lambda text: self._typing_timer_bb.start(1000))
        self.billbuy_sname.currentTextChanged.connect(lambda text: self._typing_timer_bb.start(1000))

        self.ch_billbuy_date_from.toggled.connect(lambda: self.check_date_from('bell_buy'))
        self.ch_billbuy_date_to.toggled.connect(lambda: self.check_date_to('bell_buy'))

        self.bb_page_num.valueChanged.connect(lambda text: self._typing_timer_bb.start(1000))
        self.bb_page_size.valueChanged.connect(lambda: self.change_page_size('bell_buy'))

        # print and to exel bill
        self.btn_print_table_bb.clicked.connect(self.print_table_bill_buy)
        self.btn_to_exel_bb.clicked.connect(lambda: self.to_excel(self.bb_table))

        # pages
        self.bb_post.clicked.connect(lambda: self.bb_page_num.setValue(self.bb_page_num.value() + 1))
        self.bb_previous.clicked.connect(lambda: self.bb_page_num.setValue(self.bb_page_num.value() - 1))
        self.bb_last.clicked.connect(lambda: self.bb_page_num.setValue(
            math.ceil(int(database.db.count_row("bell_buy", 1)) / self.page_size_bell_buy)))
        self.bb_first.clicked.connect(lambda: self.bb_page_num.setValue(1))

        self.btn_add_billbuy.clicked.connect(lambda: self.open_bill_buy(0))
        self.btn_edit_billbuy.clicked.connect(lambda: self.open_bill_buy(self.bill_buy_id))

        self.billbuy_date_from.setSpecialValueText(' ')
        self.billbuy_date_to.setSpecialValueText(' ')

        self.billbuy_date_from.setDate(QDate.currentDate())
        self.billbuy_date_to.setDate(QDate.currentDate())

        self.btn_edit_billbuy.setEnabled(False)

        self.update_bill_buy_table()

    def one_click_bb(self, id):
        self.bill_buy_id = id
        self.btn_edit_billbuy.setEnabled(True)

    def double_click(self, id):
        self.bill_buy_id = id
        self.open_bill_buy(id)

    def open_bill_buy(self, id):
        global DOLLAR
        if DOLLAR == 0:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'أدخل سعر تصريف الدولار بالليرة التركية من الصفحة الرئيسية')
            return
        bb = BillBuy(id)
        bb.setWindowIcon(QtGui.QIcon('emp.png'))
        bb.exec()
        self.btn_edit_billbuy.setEnabled(False)
        self.update_bill_buy_table()
        self.update_supplier_table()
        self.update_product_table()
        self.calculate_main()

    def search_bill_buy_save(self):
        fil = {}
        if self.billbuy_code.text():
            fil['code'] = self.billbuy_code.text()
        if self.billbuy_sname.currentText() != '':
            fil['s_id'] = [k for k, v in self.suppliers.items() if v == self.billbuy_sname.currentText()][0]
        if self.ch_billbuy_date_from.isChecked():
            fil['date_from'] = QDate.toString(self.billbuy_date_from.date())
            if self.ch_billbuy_date_to.isChecked():
                fil['date_to'] = QDate.toString(self.billbuy_date_to.date())

        return fil

    def update_bill_buy_table(self):
        fil = self.search_bill_buy_save()
        rows = database.db.query_all_bill("bill_buy", fil, self.page_size_bill_buy * (self.bb_page_num.value() - 1),
                                          self.page_size_bill_sell)
        self.bb_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.bb_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_bill_buy * (self.bb_page_num.value() - 1)))))
            self.bb_table.item(row_idx, 0).id = row['id']
            self.bb_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.bb_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row['code'])))
            self.bb_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            row['s_id'] = self.suppliers[row['s_id']]
            self.bb_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['s_id']))
            self.bb_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            total = str(float(row['total']) - float(row['discount']))
            self.bb_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(total))
            self.bb_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            if row['ispaid'] == '1':
                row['ispaid'] = 'مدفوعة'
            else:
                row['ispaid'] = 'غير مدفوعة'
            self.bb_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(row['ispaid']))
            self.bb_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
            self.bb_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(row['date']))
            self.bb_table.item(row_idx, 5).setTextAlignment(QtCore.Qt.AlignCenter)
        self.bb_table.resizeColumnsToContents()
        self.update_notification()

    def print_table_bill_buy(self):
        fil = self.search_bill_sell_save()
        bills = database.db.query_all_bill("bill_buy", fil, 0, database.db.count_row("bill_buy", 1))
        with open('./html/bill_buy_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, bill in enumerate(bills):
                bill['idx'] = idx + 1
                bill['s_id'] = self.suppliers[bill['s_id']]
                bill['total'] = str(float(bill['total']) - float(bill['discount']))
                if bill['ispaid'] == '1':
                    bill['ispaid'] = 'مدفوعة'
                else:
                    bill['ispaid'] = 'غير مدفوعة'
            html = template.render(bills=bills, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    ####################################################################

    # fund movement
    def setup_controls_fund_movement(self):
        self.fm_type.currentTextChanged.connect(self.fm_type_changed)
        self.fm_value.setValidator(self.validator_money)
        self.fm_value_t.setValidator(self.validator_money)

        self._typing_timer_fm.timeout.connect(self.update_fm_table)

        # table
        self.fm_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.fm_table.doubleClicked.connect(lambda mi: self.fill_fm_info(self.fm_table.item(mi.row(), 0).id))
        self.fm_table.clicked.connect(lambda mi: self.one_click_fm(self.fm_table.item(mi.row(), 0).id))
        self.fm_page_num.setRange(1, math.ceil(int(database.db.count_row("fund_movement", 1)) / self.page_size_fm))

        # search
        self.s_fm_type.currentTextChanged.connect(self.s_fm_type_changed)
        self.s_fm_owner.currentTextChanged.connect(lambda text: self._typing_timer_fm.start(1000))
        self.ch_fm_date_from.toggled.connect(lambda: self.check_date_from('fund_movement'))
        self.ch_fm_date_to.toggled.connect(lambda: self.check_date_to('fund_movement'))
        self.s_fm_note.textChanged.connect(lambda: self._typing_timer_fm.start(1000))

        self.fm_page_num.valueChanged.connect(lambda text: self._typing_timer_fm.start(1000))
        self.fm_page_size.valueChanged.connect(lambda: self.change_page_size('fund_movement'))

        # btn
        self.btn_add_fm.clicked.connect(self.create_new_fm)
        self.btn_edit_fm.clicked.connect(self.update_fm)
        self.btn_delete_fm.clicked.connect(self.delete_fm)
        self.btn_clear_fm.clicked.connect(self.clear_fm_inputs)

        # print and to exel
        self.btn_print_fm_table.clicked.connect(self.print_table_fm)
        self.btn_fm_to_exel.clicked.connect(lambda: self.to_excel(self.fm_table))

        # pages
        self.fm_post.clicked.connect(lambda: self.fm_page_num.setValue(self.fm_page_num.value() + 1))
        self.fm_previous.clicked.connect(lambda: self.fm_page_num.setValue(self.fm_page_num.value() - 1))
        self.fm_last.clicked.connect(lambda: self.fm_page_num.setValue(
            math.ceil(int(database.db.count_row("fund_movement", 1)) / self.page_size_fm)))
        self.fm_first.clicked.connect(lambda: self.fm_page_num.setValue(1))

        self.fm_date_from.setSpecialValueText(' ')
        self.fm_date_to.setSpecialValueText(' ')

        self.fm_date.setDate(QDate.currentDate())
        self.fm_date_from.setDate(QDate.currentDate())
        self.fm_date_to.setDate(QDate.currentDate())
        self.btn_edit_fm.setEnabled(False)
        self.btn_delete_fm.setEnabled(False)

        self.update_fm_table()
        self.clear_fm_inputs()

    def one_click_fm(self, id):
        self.fm_id = id
        self.btn_delete_fm.setEnabled(True)

    def fm_type_changed(self):
        if self.fm_type.currentIndex() == 1:
            self.fm_owner.setEnabled(True)
            self.fm_owner.clear()
            self.fm_owner.addItems(list(self.customers.values())[1:])
            self.fm_value_t.setEnabled(False)
        elif self.fm_type.currentIndex() == 2:
            self.fm_owner.setEnabled(True)
            self.fm_owner.clear()
            self.fm_owner.addItems(self.suppliers.values())
            self.fm_value_t.setEnabled(False)
        else:
            self.fm_owner.setEnabled(False)
            self.fm_owner.clear()
            self.fm_value_t.setEnabled(True)

    def s_fm_type_changed(self):
        if self.s_fm_type.currentIndex() == 1:
            self._typing_timer_fm.start(1000)
            self.s_fm_owner.setEnabled(True)
            self.s_fm_owner.clear()
            self.s_fm_owner.addItem('')
            self.s_fm_owner.addItems(self.customers.values())
        elif self.s_fm_type.currentIndex() == 2:
            self._typing_timer_fm.start(1000)
            self.s_fm_owner.setEnabled(True)
            self.s_fm_owner.clear()
            self.s_fm_owner.addItem('')
            self.s_fm_owner.addItems(self.suppliers.values())
        else:
            self._typing_timer_fm.start(1000)
            self.s_fm_owner.setEnabled(False)
            self.s_fm_owner.clear()

    def save_fm_info(self):
        fm = dict()
        fm['type'] = self.fm_type.currentText()
        if self.fm_type.currentIndex() == 1:
            fm['owner'] = [k for k, v in self.customers.items() if v == self.fm_owner.currentText()][0]
        elif self.fm_type.currentIndex() == 2:
            fm['owner'] = [k for k, v in self.suppliers.items() if v == self.fm_owner.currentText()][0]
        fm['value'] = self.fm_value.text()
        fm['value_t'] = self.fm_value_t.text()
        fm['date'] = QDate.toString(self.fm_date.date())
        fm['note'] = self.fm_note.toPlainText()

        return fm

    def create_new_fm(self):
        fm = self.save_fm_info()
        if fm['type']:
            if fm['type'] in ["دفعة من زبون", "دفعة إلى مورد"]:
                balance = database.db.get_balance(fm['type'], fm['owner'])
                if fm['value'] > balance:
                    QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الدفعة أكبر من الرصيد')
            database.db.insert_row("fund_movement", fm)
            toaster_Notify.QToaster.show_message(parent=self, message=f"إضافة حركة\nتم إضافة الحركة {fm['type']} بنجاح")
            self.update_fm_table()
            self.setup_box()
            self.clear_fm_inputs()
            if fm['type'] == "دفعة من زبون":
                self.update_customer_table()
            elif fm['type'] == "دفعة إلى مورد":
                self.update_supplier_table()
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل نوع الحركة')

    def update_fm(self):
        fm = self.save_fm_info()
        fm['id'] = self.fm_id
        if fm['type']:
            if fm['type'] in ["دفعة من زبون", "دفعة إلى مورد"]:
                balance = database.db.get_balance(fm['type'], fm['owner'])
                if balance > fm['value']:
                    QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الدفعة أكبر من الرصيد')
            database.db.update_row("fund_movement", fm)
            self.update_fm_table()
            self.clear_fm_inputs()
            if fm['type'] == "دفعة من زبون":
                self.update_customer_table()
            elif fm['type'] == "دفعة إلى مورد":
                self.update_supplier_table()
            self.setup_box()
            toaster_Notify.QToaster.show_message(parent=self, message=f"تعديل حركة\nتم تعديل الحركة {fm['type']} بنجاح")
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل نوع الحركة')

    def delete_fm(self):
        msg = QtWidgets.QMessageBox()
        button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف هذه الحركة؟ ", msg.Yes | msg.No, msg.No)
        if button_reply == msg.Yes:
            database.db.delete_row("fund_movement", self.fm_id)
            self.update_fm_table()
            self.setup_box()
            self.update_customer_table()
            self.update_supplier_table()
            self.clear_fm_inputs()
            toaster_Notify.QToaster.show_message(parent=self, message=f"حذف مادة\nتم حذف الحركة بنجاح")
        self.btn_delete_fm.setEnabled(False)

    def search_fm_save(self):
        fil = {}
        if self.s_fm_type.currentIndex() != 0:
            fil['type'] = self.s_fm_type.currentText()
            if self.s_fm_type.currentIndex() == 1 and self.s_fm_owner.currentText():
                fil['owner'] = [k for k, v in self.customers.items() if v == self.s_fm_owner.currentText()][0]
            elif self.s_fm_type.currentIndex() == 2 and self.s_fm_owner.currentText():
                fil['owner'] = [k for k, v in self.suppliers.items() if v == self.s_fm_owner.currentText()][0]
        if self.ch_fm_date_from.isChecked():
            fil['date_from'] = QDate.toString(self.fm_date_from.date())
            if self.ch_fm_date_to.isChecked():
                fil['date_to'] = QDate.toString(self.fm_date_to.date())
        if self.s_fm_note.toPlainText():
            fil['note'] = self.s_fm_note.toPlainText()

        return fil

    def update_fm_table(self):
        fil = self.search_fm_save()
        rows = database.db.query_all_fm(fil, self.page_size_fm * (self.fm_page_num.value() - 1), self.page_size_fm)
        self.fm_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.fm_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.page_size_fm * (self.fm_page_num.value() - 1)))))
            self.fm_table.item(row_idx, 0).id = row['id']
            self.fm_table.item(row_idx, 0).is_bill = 0
            self.fm_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            self.fm_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(row['type']))
            self.fm_table.item(row_idx, 1).setTextAlignment(QtCore.Qt.AlignCenter)
            if row['type'] == "دفعة من زبون":
                row['owner'] = self.customers[row['owner']]
            elif row['type'] == "دفعة إلى مورد":
                row['owner'] = self.suppliers[row['owner']]
            self.fm_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(row['owner']))
            self.fm_table.item(row_idx, 2).setTextAlignment(QtCore.Qt.AlignCenter)
            self.fm_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(row['value']))
            self.fm_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            self.fm_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(row['value_t']))
            self.fm_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
            self.fm_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(row['date']))
            self.fm_table.item(row_idx, 5).setTextAlignment(QtCore.Qt.AlignCenter)
            self.fm_table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(row['note']))
            self.fm_table.item(row_idx, 6).setTextAlignment(QtCore.Qt.AlignCenter)

        self.fm_table.resizeColumnsToContents()

    def clear_fm_inputs(self):
        self.fm_id = 0
        self.fm_type.setCurrentIndex(0)
        self.fm_type.setFocus()
        self.fm_owner.setCurrentIndex(0)
        self.fm_value.setText('0')
        self.fm_value_t.setText('0')
        self.fm_date.setDate(QDate.currentDate())
        self.fm_note.clear()

        self.btn_edit_fm.setEnabled(False)
        self.btn_delete_fm.setEnabled(False)
        self.btn_add_fm.setEnabled(True)

    def fill_fm_info(self, id):
        self.btn_edit_fm.setEnabled(True)
        self.btn_delete_fm.setEnabled(True)
        self.btn_add_fm.setEnabled(False)
        self.fm_id = id
        fm = database.db.query_row("fund_movement", id)
        if fm:
            self.fm_type.setCurrentText(fm['type'])
            if fm['type'] == "دفعة من زبون":
                self.fm_owner.setCurrentText(self.customers[fm['owner']])
            elif fm['type'] == "دفعة إلى مورد":
                self.fm_owner.setCurrentText(self.suppliers[fm['owner']])
            self.fm_value.setText(fm['value'])
            self.fm_value_t.setText(fm['value_t'])
            self.fm_date.setDate(QDate(fm['date']))
            self.fm_note.setText(fm['note'])

    def print_table_fm(self):
        fil = self.search_fm_save()
        fms = database.db.query_all_fm(fil, 0, database.db.count_row("fund_movement", 1))
        with open('./html/fm_template.html', 'r') as f:
            template = Template(f.read())
            fp = tempfile.NamedTemporaryFile(mode='w', delete=False, dir='./html/tmp/', suffix='.html')
            for idx, fm in enumerate(fms):
                fm['idx'] = idx + 1
                if fm['type'] == "دفعة من زبون":
                    fm['owner'] = self.customers[fm['owner']]
                elif fm['type'] == "دفعة إلى مورد":
                    fm['owner'] = self.suppliers[fm['owner']]
            html = template.render(fms=fms, date=time.strftime("%A, %d %B %Y %I:%M %p"))
            html = html.replace('style.css', '../style.css').replace('ph1.png', '../ph1.png')
            fp.write(html)
            fp.close()
            os.system('setsid firefox ' + fp.name + ' &')

    # #################################################################

    # export tables to exel
    def to_excel(self, table):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', '', ".xlsx(*.xlsx)")
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet("sheet", cell_overwrite_ok=True)
        sheet.cols_right_to_left = True
        style = xlwt.XFStyle()
        font = xlwt.Font()
        font.bold = True
        style.font = font
        model = table.model()
        for c in range(1, model.columnCount()):
            text = model.headerData(c, QtCore.Qt.Horizontal)
            sheet.write(0, c - 1, text, style=style)

        for c in range(1, model.columnCount()):
            for r in range(model.rowCount()):
                text = model.data(model.index(r, c))
                sheet.write(r + 1, c - 1, text)
        try:
            wbk.save(file_name)
        except IOError:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يوجد خطأ في حفظ الملف')

    def update_notification(self):
        pro1 = database.db.get_noti_pro1()
        pro2 = database.db.get_noti_pro2()
        pro = pro1 + pro2
        cus = database.db.get_noti_cus("customer")
        sus = database.db.get_noti_cus("supplier")
        csus = cus + sus
        all_list = pro + csus
        self.notif_table.setRowCount(len(all_list))
        for row_idx, row in enumerate(pro2):
            self.notif_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.n_page_size.value() * (self.n_page_num.value() - 1)))))
            self.notif_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            noti = f"إن المادة {row['name']} ذات الكود  {row['code']}  انتهت بالفعل "
            self.notif_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(noti))
        for row_idx, row in enumerate(pro1):
            row_idx += len(pro2)
            self.notif_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.n_page_size.value() * (self.n_page_num.value() - 1)))))
            self.notif_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            noti = f"إن المادة {row['name']} ذات الكود  {row['code']}  شارفت على الانتهاء"
            self.notif_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(noti))
        for row_idx, row in enumerate(csus):
            row_idx += len(pro)
            self.notif_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(
                str(row_idx + 1 + (self.n_page_size.value() * (self.n_page_num.value() - 1)))))
            self.notif_table.item(row_idx, 0).setTextAlignment(QtCore.Qt.AlignCenter)
            noti = f"إن السيد المحترم {row['name']} بلغ الحد المسموح به وهو {row['range_balance']}"
            self.notif_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(noti))
        self.notif_table.resizeColumnsToContents()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    locale.setlocale(locale.LC_ALL, "en_US.utf8")
    # ser = os.popen("wmic bios get serialnumber").read().replace("\n", "").replace("	", "").replace(" ", "")
    # ser = subprocess.run("sed -nr 's/^Serial Number: (.*)$/\1/p' /proc/scsi/*/*")
    
    # if ser == SerialNumber:
    mainWindow = AppMainWindow()
    mainWindow.show()
    mainWindow.setWindowIcon(QtGui.QIcon('icons/ph1.png'))
    for filename in glob.glob("html/tmp/*"):
        os.remove(filename)
    exit_code = app.exec_()
    # else:
    #     QtWidgets.QMessageBox.warning(None, 'خطأ', 'البرنامج غير مفعل\n يجب تفعيل هذا البرنامج من الشركة')
