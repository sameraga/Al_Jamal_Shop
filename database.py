from sqlcipher3 import dbapi2 as sqlite

db = None


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        value = row[idx]
        key = col[0]
        if isinstance(value, int):
            d[key] = str(value)
        else:
            d[key] = value
    return d


class Database:
    def __init__(self, database_path):
        self.connection = sqlite.connect(database_path)
        self.connection.row_factory = _dict_factory

    @staticmethod
    def open_database():
        global db
        db = Database('j_shop.db')

    def change_user_pass(self, username, password):
        self.connection.execute('UPDATE users SET pass = ? WHERE users.name = ?', (password, username))
        self.connection.commit()

    def is_user(self, username):
        return self.connection.execute('select pass from users where name = ?', (username,)).fetchone()

    def query_all_medicine(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, name, type, unit, amount, factory, production_date, expiry_date from medicine"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')
            if 'factory' in filter:
                filter['factory'] = f'%{filter["factory"]}%'
                filter_cmd.append(f'factory like :factory')
            if 'type' in filter:
                filter['type'] = f'%{filter["type"]}%'
                filter_cmd.append(f'type like :type')

            if 'expiry_date_f' in filter:
                if 'expiry_date_t' in filter:
                    filter_cmd.append(f'expiry_date between :expiry_date_f and :expiry_date_t')
                else:
                    filter_cmd.append(f'expiry_date = :expiry_date_f')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    def insert_medicine(self, medicine):
        cursor = self.connection.cursor()

        columns = ', '.join(medicine.keys())
        placeholders = ':' + ', :'.join(medicine.keys())

        query = f'INSERT INTO medicine ({columns}) VALUES ({placeholders})'
        cursor.execute(query, medicine)
        self.connection.commit()

    def delete_medicine(self, code):
        self.connection.execute('delete from medicine where code = ?', (code,))
        self.connection.commit()

    def update_medicine(self, medicine, id):
        placeholders = ', '.join([f'{key}=:{key}' for key in medicine.keys()])
        query = f'UPDATE medicine SET {placeholders} WHERE id={id}'
        self.connection.execute(query, medicine)
        self.connection.commit()

    def count_medicine(self, r):
        if r == 1:
            return self.connection.execute('select count(*) as count from medicine').fetchone()['count']
        else:
            return self.connection.execute('select count(*) as count from medicine where code = ?', (r,)).fetchone()['count']

    def query_medicine(self, id):
        return self.connection.execute('select * from medicine where id = ?', (id,)).fetchone()

    def get_medicine_next_id(self):
        return self.connection.execute("select seq+1 as seq from sqlite_sequence where name = 'medicine'").fetchone()['seq']

    def get_medicine_by_code(self, code):
        return self.connection.execute('SELECT * from medicine WHERE code = ?', (code,)).fetchone()

    def query_medicines_by_rd(self, rds):
        sql_cmd = f"SELECT * from medicine WHERE code IN ({','.join(['?'] * len(rds))})"
        return self.connection.execute(sql_cmd, rds).fetchall()

    def query_medicine_by_ids(self, ids, simple=False):
        if simple:
            sql_cmd = (
                "SELECT id, name from medicine"
                f"WHERE id IN ({','.join(['?'] * len(ids))})"
            )
        else:
            sql_cmd = f"SELECT * from medicine WHERE id IN ({','.join(['?'] * len(ids))})"
        return self.connection.execute(sql_cmd, ids).fetchall()

    # customer methods database #
    def query_customer(self, id):
        return self.connection.execute('select * from customer where id = ?', (id,)).fetchone()

    def query_all_customer(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, name, phone, health_status, age, balance from customer"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')
            if 'phone' in filter:
                filter['phone'] = f'%{filter["phone"]}%'
                filter_cmd.append(f'phone like :phone')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    def get_customer_next_id(self):
        return self.connection.execute("select seq+1 as seq from sqlite_sequence where name = 'customer'").fetchone()['seq']

    def get_customer_by_code(self, code):
        return self.connection.execute('SELECT * from customer WHERE code = ?', (code,)).fetchone()

    def count_customer(self, r):
        if r == 1:
            return self.connection.execute('select count(*) as count from customer').fetchone()['count']
        else:
            return self.connection.execute('select count(*) as count from customer where code = ?', (r,)).fetchone()['count']

    def insert_customer(self, customer):
        cursor = self.connection.cursor()

        columns = ', '.join(customer.keys())
        placeholders = ':' + ', :'.join(customer.keys())

        query = f'INSERT INTO customer ({columns}) VALUES ({placeholders})'
        cursor.execute(query, customer)
        self.connection.commit()

    def delete_customer(self, code):
        self.connection.execute('delete from customer where code = ?', (code,))
        self.connection.commit()

    def update_customer(self, customer, id):
        placeholders = ', '.join([f'{key}=:{key}' for key in customer.keys()])
        query = f'UPDATE customer SET {placeholders} WHERE id={id}'
        self.connection.execute(query, customer)
        self.connection.commit()

    def query_customer_by_ids(self, ids, simple=False):
        if simple:
            sql_cmd = (
                "SELECT id, name from customer"
                f"WHERE id IN ({','.join(['?'] * len(ids))})"
            )
        else:
            sql_cmd = f"SELECT * from customer WHERE id IN ({','.join(['?'] * len(ids))})"
        return self.connection.execute(sql_cmd, ids).fetchall()

    def query_customers_by_rd(self, rds):
        sql_cmd = f"SELECT * from customer WHERE code IN ({','.join(['?'] * len(rds))})"
        return self.connection.execute(sql_cmd, rds).fetchall()

    # supplier methods database #
    def query_supplier(self, id):
        return self.connection.execute('select * from supplier where id = ?', (id,)).fetchone()

    def query_all_supplier(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, name, phone, name_delegate, phone_delegate, address, balance from supplier"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')
            if 'phone' in filter:
                filter['phone'] = f'%{filter["phone"]}%'
                filter_cmd.append(f'phone_delegate like :phone')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    def get_supplier_next_id(self):
        return self.connection.execute("select seq+1 as seq from sqlite_sequence where name = 'supplier'").fetchone()['seq']

    def get_supplier_by_code(self, code):
        return self.connection.execute('SELECT * from supplier WHERE code = ?', (code,)).fetchone()

    def count_supplier(self, r):
        if r == 1:
            return self.connection.execute('select count(*) as count from supplier').fetchone()['count']
        else:
            return self.connection.execute('select count(*) as count from supplier where code = ?', (r,)).fetchone()['count']

    def insert_supplier(self, supplier):
        cursor = self.connection.cursor()

        columns = ', '.join(supplier.keys())
        placeholders = ':' + ', :'.join(supplier.keys())

        query = f'INSERT INTO supplier ({columns}) VALUES ({placeholders})'
        cursor.execute(query, supplier)
        self.connection.commit()

    def delete_supplier(self, code):
        self.connection.execute('delete from supplier where code = ?', (code,))
        self.connection.commit()

    def update_supplier(self, supplier, id):
        placeholders = ', '.join([f'{key}=:{key}' for key in supplier.keys()])
        query = f'UPDATE supplier SET {placeholders} WHERE id={id}'
        self.connection.execute(query, supplier)
        self.connection.commit()

    def query_supplier_by_ids(self, ids, simple=False):
        if simple:
            sql_cmd = (
                "SELECT id, name from supplier"
                f"WHERE id IN ({','.join(['?'] * len(ids))})"
            )
        else:
            sql_cmd = f"SELECT * from supplier WHERE id IN ({','.join(['?'] * len(ids))})"
        return self.connection.execute(sql_cmd, ids).fetchall()

    def query_suppliers_by_rd(self, rds):
        sql_cmd = f"SELECT * from supplier WHERE code IN ({','.join(['?'] * len(rds))})"
        return self.connection.execute(sql_cmd, rds).fetchall()

    # bill sell methods
    def get_bills_next_id(self):
        return self.connection.execute("select seq+1 as seq from sqlite_sequence where name = 'bill_sell'").fetchone()['seq']

    def get_cname(self):
        return {e['id']: e['name'] for e in self.connection.execute('select id, name from customer').fetchall()}

    def get_cphone(self, name):
        return self.connection.execute('select phone from customer where name = ?', (name,)).fetchone()
    # CREATE VIEW order_bill as SELECT order.m_id, medicine.name, medicine.unit, order.amount, medicine.sell_price, order.amount * medicine.sell_price as total, order.discount, total - order.discount as final FROM medicine, order
