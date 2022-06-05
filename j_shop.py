#!/usr/bin/env python3

import glob
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
import PyQt5.uic as uic
import hashlib

import toaster_Notify
from QDate import QDate
import database

Form_Main, _ = uic.loadUiType('j_shop.ui')
Form_BillSell, _ = uic.loadUiType('bill_sell.ui')
PAGE_SIZE = 10
USER = ''
PASS = ''


class ReadOnlyDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        # print('createEditor event fired')
        return


class BillSell(QtWidgets.QDialog, Form_BillSell):
    def __init__(self, id):
        QtWidgets.QDialog.__init__(self)
        Form_BillSell.__init__(self)
        self.setupUi(self)

        self.validator_money = QtGui.QRegExpValidator(
            QtCore.QRegExp('^(\$)?(([1-9]\d{0,2}(\,\d{3})*)|([1-9]\d*)|(0))(\.\d{2})?$'))

        if id == 0:
            self.bill_code.setText(str(int(database.db.get_bills_next_id()) + 10000))
        else:
            self.bill_code.setText(str(id))

        self.setup_control()

    def setup_control(self):
        self.b_date.setDate(QDate.currentDate())
        self.discount.setValidator(self.validator_money)

        self.c_name.clear()
        self.c_name.addItem('')
        self.c_name.addItems(database.db.query_customer().values())
        self.c_name.currentTextChanged.connect(lambda: self.c_phone.setText(database.db.get_customer_phone_by_name(self.c_name.currentText())))

        self.bs_table: QtWidgets.QTableWidget
        delegate = ReadOnlyDelegate(self.bs_table)
        self.bs_table.setItemDelegateForColumn(3, delegate)
        self.bs_table.setItemDelegateForColumn(5, delegate)
        self.bs_table.setRowCount(1)
        self.bs_table.keyReleaseEvent = self.table_key_press_event

        self.discount.returnPressed.connect(self.discount_on_press)

    def table_key_press_event(self, event: QtGui.QKeyEvent):
        self.bs_table: QtWidgets.QTableWidget
        if event.key() == QtCore.Qt.Key_Return:
            if self.bs_table.currentColumn() == 0 and self.bs_table.currentRow() + 1 == self.bs_table.rowCount():
                self.update_table(self.bs_table.currentRow())
            else:
                self.enter_event(self.bs_table.currentRow())

    def update_table(self, current_row):
        code = self.bs_table.item(current_row, 0).text()
        product = database.db.get_product_by_code(code)
        if product:
            self.bs_table.item(current_row, 0).id = product['id']
            self.bs_table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(product['name']))
            self.bs_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem('1'))
            self.bs_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(product['sell_price'])))
            self.bs_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem('0'))
            self.bs_table.setItem(current_row, 5, QtWidgets.QTableWidgetItem(str(product['sell_price'])))
            self.bs_table.setRowCount(self.bs_table.rowCount() + 1)
            btn_delete = QtWidgets.QPushButton(QtGui.QIcon.fromTheme('delete'), '')
            btn_delete.clicked.connect(lambda: self.bs_table.removeRow(current_row))
            self.bs_table.setCellWidget(current_row, 6, btn_delete)
            self.calculate_total()
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'الرقم غير موجود\n أعد ادخال رقم صحيح')

    def enter_event(self, current_row):
        code = self.bs_table.item(current_row, 0).text()
        product = database.db.get_product_by_code(code)
        discount = float(self.bs_table.item(current_row, 4).text())
        quantity = int(self.bs_table.item(current_row, 2).text())
        if discount > (float(product['price_range']) * quantity):
            discount = float(product['price_range']) * quantity
            self.bs_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem(str(discount)))
        total = quantity * float(product['sell_price']) - discount
        self.bs_table.setItem(current_row, 5, QtWidgets.QTableWidgetItem(str(total)))
        self.calculate_total()

    def calculate_total(self):
        total = 0
        for i in range(0, self.bs_table.rowCount()):
            if self.bs_table.item(i, 5) is not None:
                total += float(self.bs_table.item(i, 5).text())
        self.total.setText(str(total))

    def discount_on_press(self):
        self.last_total.setText(str(float(self.total.text()) - float(self.discount.text())))


def open_bill_sell(id):
    sb = BillSell(id)
    sb.setWindowIcon(QtGui.QIcon('emp.png'))
    sb.exec()


class AppMainWindow(QtWidgets.QMainWindow, Form_Main):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Form_Main.__init__(self)
        self.setupUi(self)

        self.validator_code = QtGui.QRegExpValidator(QtCore.QRegExp('[a-z][0-9]*'))
        self.validator_money = QtGui.QRegExpValidator(QtCore.QRegExp('^(\$)?(([1-9]\d{0,2}(\,\d{3})*)|([1-9]\d*)|(0))(\.\d{2})?$'))

        self._typing_timer_p = QtCore.QTimer()
        self.product_id = 0
        self.product_co = 0
        self.page_size_product = PAGE_SIZE

        self._typing_timer_c = QtCore.QTimer()
        self.customer_id = 0
        self.customer_co = 0
        self.page_size_customer = PAGE_SIZE

        self.customers = None

        self._typing_timer_s = QtCore.QTimer()
        self.supplier_id = 0
        self.supplier_co = 0
        self.page_size_supplier = PAGE_SIZE

        self._typing_timer_bs = QtCore.QTimer()
        self.bill_sell_id = 0
        self.bill_sell_co = 0
        self.page_size_bill_sell = PAGE_SIZE

        self.setup_login()

    def setup_login(self):
        self.menubar.setVisible(False)
        self.txt_username.setFocus()
        self.btn_in.clicked.connect(self.enter_app)
        self.btn_exit.clicked.connect(lambda: sys.exit(1))

    def enter_app(self):
        global PASS
        global USER
        s = '1'
        PASS = hashlib.sha256(s.encode()).digest()
        PASS = hashlib.sha256(self.txt_password.text().encode()).digest()
        USER = self.txt_username.text()

        database.Database.open_database()
        p: dict = database.db.is_user(USER)
        if p and 'pass' in p and p['pass'] == PASS:
            self.setup_controls()
            self.stackedWidget.setCurrentIndex(0)
        else:
            self.lbl_wrong.setText('* اسم المستخدم أو كلمة المرور غير صحيحة !!!')

    def change_pass_(self):
        self.stackedWidget.setCurrentIndex(2)
        self.menubar.setVisible(False)
        self.old_pass.setFocus()
        self.btn_save_pass.clicked.connect(self.save_new_pass)
        self.btn_cancel_pass.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))

    def save_new_pass(self):
        global PASS
        if self.old_pass.text() == PASS:
            if self.new_pass.text() == self.new_pass_confirm.text():
                if self.new_pass.text() != '':
                    PASS = hashlib.sha256(self.new_pass.text().encode()).digest()
                    database.db.change_user_pass(USER, PASS)
                    self.stackedWidget.setCurrentIndex(0)
                    toaster_Notify.QToaster.show_message(parent=self, message="تغيير كلمة المرور\nتم تغيير كلمة المرور بنجاح")
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

        self.customers = database.db.query_customer()

        # update tables
        self._typing_timer_p.setSingleShot(True)
        self._typing_timer_c.setSingleShot(True)
        self._typing_timer_s.setSingleShot(True)
        self._typing_timer_bs.setSingleShot(True)

        self.change_pass.triggered.connect(self.change_pass_)
        self.exit.triggered.connect(lambda: sys.exit(1))

        self.setup_controls_product()
        self.setup_controls_customer()
        self.setup_controls_supplier()
        self.setup_controls_bill_sell()

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
            self.bs_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_sell", 1)) / self.page_size_bill_sell))
            self._typing_timer_bs.start(1000)

    def check_date_from(self, x):
        if x == 'bell_sell':
            self._typing_timer_bs.start(1000)
            if self.ch_billsell_date_from.isChecked():
                self.billsell_date_from.setEnabled(True)
                self.billsell_date_from.dateChanged.connect(lambda: self._typing_timer_bs.start(1000))
                self.ch_billsell_date_to.setEnabled(True)
            else:
                self.billsell_date_from.setEnabled(False)
                self.ch_billsell_date_to.setEnabled(False)
                self.billsell_date_to.setEnabled(False)
                self.ch_billsell_date_to.setChecked(False)

    def check_date_to(self, x):
        if x == 'bell_sell':
            self._typing_timer_bs.start(1000)
            if self.ch_billsell_date_to.isChecked():
                self.billsell_date_to.setEnabled(True)
                self.billsell_date_to.dateChanged.connect(lambda: self._typing_timer_bs.start(1000))
            else:
                self.billsell_date_to.setEnabled(False)

    ####################################################################

    # product methods
    def setup_controls_product(self):
        self.p_code.setValidator(self.validator_code)
        self.p_code_search.setValidator(self.validator_code)
        self._typing_timer_p.timeout.connect(self.update_product_table)

        # table
        self.p_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.p_table.doubleClicked.connect(lambda mi: self.fill_product_info(self.p_table.item(mi.row(), 0).id))
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
        self.p_last.clicked.connect(lambda: self.p_page_num.setValue(math.ceil(int(database.db.count_row("product", 1)) / self.page_size_product)))
        self.p_first.clicked.connect(lambda: self.p_page_num.setValue(1))

        self.btn_edit_product.setEnabled(False)
        self.btn_delete_product.setEnabled(False)

        self.update_product_table()
        self.clear_product_inputs()

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
            self.bs_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_sell", 1)) / self.page_size_bill_sell))
            self._typing_timer_bs.start(1000)

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
            if int(database.db.count_row("product", product['code'])) == 0:
                database.db.insert_row("product", product)
                toaster_Notify.QToaster.show_message(parent=self, message=f"إضافة مادة\nتم إضافة المادة{product['name']} بنجاح")
                self.update_product_table()
                self.clear_product_inputs()
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المادة')

    def update_product(self):
        product = self.save_product_info()
        if product['code'] and product['name']:
            if product['code'] == self.product_co:
                database.db.update_row("product", product, self.product_id)
                self.update_product_table()
                self.clear_product_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مادة\nتم تعديل المادة{product['name']} بنجاح")
            elif int(database.db.count_row("product", product['code'])) == 0:
                database.db.update_row("product", product, self.product_id)
                self.update_product_table()
                self.clear_product_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مادة\nتم تعديل المادة{product['name']} بنجاح")
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المادة')

    def delete_product(self):
        product = self.save_product_info()
        msg = QtWidgets.QMessageBox()
        if product['code']:
            button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {product['name']} ؟ ",
                                        msg.Yes | msg.No,
                                        msg.No)
            if button_reply == msg.Yes:
                database.db.delete_row("product", self.product_id)
                self.update_product_table()
                self.clear_product_inputs()
                toaster_Notify.QToaster.show_message(parent=self, message=f"حذف مادة\nتم حذف المادة{product['name']} بنجاح")
        else:
            QtWidgets.QMessageBox.warning(
                None, 'خطأ', 'الرقم غير موجود\n أعد الضغط على اسم المادة التي تريد من الجدول')

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
        rows = database.db.query_all_product(fil, self.page_size_product * (self.p_page_num.value() - 1), self.page_size_product)
        self.p_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.p_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row_idx + 1 + (self.page_size_product * (self.p_page_num.value() - 1)))))
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
            self.p_table.setItem(row_idx, 7, QtWidgets.QTableWidgetItem(row['sell_price']))
            self.p_table.item(row_idx, 7).setTextAlignment(QtCore.Qt.AlignCenter)
            self.p_table.setItem(row_idx, 8, QtWidgets.QTableWidgetItem(row['source']))
            self.p_table.item(row_idx, 8).setTextAlignment(QtCore.Qt.AlignCenter)
        self.p_table.resizeColumnsToContents()

    def clear_product_inputs(self):
        self.product_id = 0
        self.product_co = 0

        self.p_code.clear()
        self.p_code.setFocus()
        self.p_name.clear()
        self.p_class.setCurrentIndex(0)
        self.p_type.setCurrentIndex(0)
        self.p_source.clear()
        self.p_quantity.clear()
        self.p_less_quantity.clear()
        self.p_buy_price.clear()
        self.p_sell_price.clear()
        self.p_sell_price_wh.clear()
        self.p_price_range.clear()

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

        self._typing_timer_c.timeout.connect(self.update_customer_table)

        # table
        self.c_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.c_table.doubleClicked.connect(lambda mi: self.fill_customer_info(self.c_table.item(mi.row(), 0).id))
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

    def save_customer_info(self):
        customer = dict()
        customer['code'] = self.c_code.text()
        customer['name'] = self.c_name.text()
        customer['phone'] = self.c_phone.text()
        customer['balance'] = self.c_balance.text()
        customer['note'] = self.c_note.toPlainText()

        return customer

    def create_new_customer(self):
        customer = self.save_customer_info()
        if customer['code'] and customer['name']:
            if int(database.db.count_row("customer", customer['code'])) == 0:
                database.db.insert_row("customer", customer)
                toaster_Notify.QToaster.show_message(parent=self, message=f"إضافة زبون\nتم إضافة الزبون{customer['name']} بنجاح")
                self.update_customer_table()
                self.clear_customer_inputs()
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم الزبون')

    def update_customer(self):
        customer = self.save_customer_info()
        if customer['code'] and customer['name']:
            if customer['code'] == self.customer_co:
                database.db.update_row("customer", customer, self.customer_id)
                self.update_customer_table()
                self.clear_customer_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل زبون\nتم تعديل الزبون{customer['name']} بنجاح")
            elif int(database.db.count_row("customer", customer['code'])) == 0:
                database.db.update_row("customer", customer, self.customer_id)
                self.update_customer_table()
                self.clear_customer_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل زبون\nتم تعديل الزبون{customer['name']} بنجاح")
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم الزبون')

    def delete_customer(self):
        customer = self.save_customer_info()
        msg = QtWidgets.QMessageBox()
        if customer['code']:
            button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {customer['name']} ؟ ",
                                        msg.Yes | msg.No,
                                        msg.No)
            if button_reply == msg.Yes:
                database.db.delete_medicine(customer['code'])
                self.update_customer_table()
                self.clear_customer_inputs()
                toaster_Notify.QToaster.show_message(parent=self, message=f"حذف زبون\nتم حذف الزبون{customer['name']} بنجاح")
        else:
            QtWidgets.QMessageBox.warning(
                None, 'خطأ', 'الرقم غير موجود\n أعد الضغط على اسم الزبون الذي تريد من الجدول')

    def search_customer_save(self):
        fil = {}
        if self.c_code_search.text():
            fil['code'] = self.c_code_search.text()
        if self.c_name_search.text():
            fil['name'] = self.c_name_search.text()

        return fil

    def update_customer_table(self):
        fil = self.search_customer_save()
        rows = database.db.query_all_customer(fil, self.page_size_customer * (self.c_page_num.value() - 1), self.page_size_customer)
        self.c_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.c_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row_idx + 1 + (self.page_size_customer * (self.c_page_num.value() - 1)))))
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
        self.p_table.resizeColumnsToContents()

    def clear_customer_inputs(self):
        self.customer_id = 0
        self.customer_co = 0

        self.c_code.clear()
        self.c_code.setFocus()
        self.c_name.clear()
        self.c_phone.clear()
        self.c_balance.setText('0')
        self.c_note.clear()

        self.btn_edit_customer.setEnabled(False)
        self.btn_delete_customer.setEnabled(False)
        self.btn_add_customer.setEnabled(True)

    def fill_customer_info(self, id):
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
            self.c_balance.setText(customer['balance'])
            self.c_note.setText(customer['note'])

    def print_table_customer(self):
        fil = self.search_customer_save()
        customer = database.db.query_all_medicine(fil, 0, database.db.count_row("customer", 1))
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

    # supplier methods
    def setup_controls_supplier(self):
        self.s_code.setValidator(self.validator_code)
        self.s_code_search.setValidator(self.validator_code)
        self.s_balance.setValidator(self.validator_money)

        self._typing_timer_s.timeout.connect(self.update_supplier_table)

        # table
        self.s_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.s_table.doubleClicked.connect(lambda mi: self.fill_supplier_info(self.s_table.item(mi.row(), 0).id))
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

    def save_supplier_info(self):
        supplier = dict()
        supplier['code'] = self.s_code.text()
        supplier['name'] = self.s_name.text()
        supplier['phone'] = self.s_phone.text()
        supplier['address'] = self.s_address.toPlainText()
        supplier['balance'] = self.s_balance.text()
        supplier['note'] = self.s_note.toPlainText()

        return supplier

    def create_new_supplier(self):
        supplier = self.save_supplier_info()
        if supplier['code'] and supplier['name']:
            if int(database.db.count_row("supplier", supplier['code'])) == 0:
                database.db.insert_row("supplier", supplier)
                toaster_Notify.QToaster.show_message(parent=self, message=f"إضافة مورد\nتم إضافة المورد{supplier['name']} بنجاح")
                self.update_supplier_table()
                self.clear_supplier_inputs()
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المورد')

    def update_supplier(self):
        supplier = self.save_supplier_info()
        if supplier['code'] and supplier['name']:
            if supplier['code'] == self.supplier_co:
                database.db.update_row("supplier", supplier, self.supplier_id)
                self.update_supplier_table()
                self.clear_supplier_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مورد\nتم تعديل المورد{supplier['name']} بنجاح")
            elif int(database.db.count_row("supplier", supplier['code'])) == 0:
                database.db.update_row("supplier", supplier, self.supplier_id)
                self.update_supplier_table()
                self.clear_supplier_inputs()
                toaster_Notify.QToaster.show_message(parent=self,
                                                     message=f"تعديل مورد\nتم تعديل المورد{supplier['name']} بنجاح")
            else:
                QtWidgets.QMessageBox.warning(None, 'خطأ', 'إن الكود مكرر')
        else:
            QtWidgets.QMessageBox.warning(None, 'خطأ', 'يجب أن تدخل الكود واسم المورد')

    def delete_supplier(self):
        supplier = self.save_supplier_info()
        msg = QtWidgets.QMessageBox()
        if supplier['code']:
            button_reply = msg.question(self, 'تأكيد', f"هل أنت متأكد من حذف {supplier['name']} ؟ ",
                                        msg.Yes | msg.No,
                                        msg.No)
            if button_reply == msg.Yes:
                database.db.delete_row("supplier", self.supplier_id)
                self.update_supplier_table()
                self.clear_supplier_inputs()
                toaster_Notify.QToaster.show_message(parent=self, message=f"حذف مورد\nتم حذف المورد{supplier['name']} بنجاح")
        else:
            QtWidgets.QMessageBox.warning(
                None, 'خطأ', 'الرقم غير موجود\n أعد الضغط على اسم المورد الذي تريد من الجدول')

    def search_supplier_save(self):
        fil = {}
        if self.s_code_search.text():
            fil['code'] = self.s_code_search.text()
        if self.s_name_search.text():
            fil['name'] = self.s_name_search.text()

        return fil

    def update_supplier_table(self):
        fil = self.search_supplier_save()
        rows = database.db.query_all_supplier(fil, self.page_size_supplier * (self.s_page_num.value() - 1), self.page_size_supplier)
        self.s_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.s_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row_idx + 1 + (self.page_size_supplier * (self.s_page_num.value() - 1)))))
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
            self.s_note.setText(supplier['note'])

    def print_table_supplier(self):
        fil = self.search_supplier_save()
        suppliers = database.db.query_all_supplier(fil, 0, database.db.count_row("supplier", 1))
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
        self.bs_table.doubleClicked.connect(lambda mi: self.double_click(self.bs_table.item(mi.row(), 0).id))
        self.bs_table.clicked.connect(lambda mi: self.one_click(self.bs_table.item(mi.row(), 0).id))
        self.bs_page_num.setRange(1, math.ceil(int(database.db.count_row("bill_sell", 1)) / self.page_size_bill_sell))

        self.billsell_code.textChanged.connect(lambda text: self._typing_timer_bs.start(1000))
        self.billsell_cname.currentTextChanged.connect(lambda text: self._typing_timer_bs.start(1000))

        self.ch_billsell_date_from.toggled.connect(lambda: self.check_date_from('bell_sell'))
        self.ch_billsell_date_to.toggled.connect(lambda: self.check_date_to('bell_sell'))

        self.bs_page_num.valueChanged.connect(lambda text: self._typing_timer_bs.start(1000))
        self.bs_page_size.valueChanged.connect(lambda: self.change_page_size('bell_sell'))

        # print and to exel
        self.btn_print_table_bs.clicked.connect(self.print_table_bell_sell)
        self.btn_to_exel_bs.clicked.connect(lambda: self.to_excel(self.bs_table))

        # pages
        self.bs_post.clicked.connect(lambda: self.bs_page_num.setValue(self.bs_page_num.value() + 1))
        self.bs_previous.clicked.connect(lambda: self.bs_page_num.setValue(self.bs_page_num.value() - 1))
        self.bs_last.clicked.connect(lambda: self.bs_page_num.setValue(
            math.ceil(int(database.db.count_row("bell_sell", 1)) / self.page_size_bell_sell)))
        self.bs_first.clicked.connect(lambda: self.bs_page_num.setValue(1))

        self.btn_add_billsell.clicked.connect(lambda: open_bill_sell(0))
        self.btn_edit_billsell.clicked.connect(lambda: open_bill_sell(self.bill_sell_id))

        self.billsell_date_from.setSpecialValueText(' ')
        self.billsell_date_to.setSpecialValueText(' ')

        self.btn_edit_billsell.setEnabled(False)

        self.billsell_date_from.setEnabled(False)
        self.ch_billsell_date_to.setEnabled(False)
        self.billsell_date_to.setEnabled(False)

        self.update_bill_sell_table()

    def one_click(self, id):
        self.bill_sell_id = id
        self.btn_edit_billsell.setEnabled(True)

    def double_click(self, id):
        self.bill_sell_id = id
        open_bill_sell(id)

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
        rows = database.db.query_all_bill_sell(fil, self.page_size_bill_sell * (self.bs_page_num.value() - 1), self.page_size_bill_sell)
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
            self.bs_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(row['total'])))
            self.bs_table.item(row_idx, 3).setTextAlignment(QtCore.Qt.AlignCenter)
            if row['ispaid'] == 1:
                row['ispaid'] = 'مدفوعة'
            else:
                row['ispaid'] = 'غير مدفوعة'
            self.bs_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(row['ispaid']))
            self.bs_table.item(row_idx, 4).setTextAlignment(QtCore.Qt.AlignCenter)
            self.bs_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(row['date']))
            self.bs_table.item(row_idx, 5).setTextAlignment(QtCore.Qt.AlignCenter)
        self.bs_table.resizeColumnsToContents()

    def print_table_bell_sell(self):
        print("222")

    def print_table_bell_sell2(self):
        print("111")
    ####################################################################

    # export tables to exel
    def to_excel(self, table):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', '', ".dot(*.exel)")
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet("sheet", cell_overwrite_ok=True)
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    locale.setlocale(locale.LC_ALL, "en_US.utf8")

    mainWindow = AppMainWindow()
    mainWindow.show()
    mainWindow.setWindowIcon(QtGui.QIcon('icons/ph1.png'))
    for filename in glob.glob("html/tmp/*"):
        os.remove(filename)
    exit_code = app.exec_()
