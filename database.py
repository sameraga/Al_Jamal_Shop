from sqlcipher3 import dbapi2 as sqlite

db = None


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        value = row[idx]
        key = col[0]
        if isinstance(value, int):
            d[key] = str(value)
        elif isinstance(value, float):
            d[key] = str(value)
        elif value:
            d[key] = value
        else:
            d[key] = ''
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
        return self.connection.execute(f"select pass from users where name = '{username}'").fetchone()

    def count_row(self, table, r):
        if r == 1:
            return self.connection.execute(f'select count(*) as count from {table}').fetchone()['count']
        else:
            return self.connection.execute(f'select count(*) as count from {table} where code = ?', (r,)).fetchone()['count']

    def get_next_id(self, table):
        if self.connection.execute(f"select max(id)+1 as seq from {table}").fetchone()['seq'] == '':
            return 1
        return self.connection.execute(f"select max(id)+1 as seq from {table}").fetchone()['seq']

    def query_row(self, table, id):
        return self.connection.execute(f"select * from {table} where id = {id}").fetchone()

    def query_csp(self, table):
        return {e['id']: e['name'] for e in self.connection.execute(f'select id, name from {table}').fetchall()}

    def get_id_by_code(self, table, code):
        return self.connection.execute(f"select id from {table} where code = '{code}'").fetchone()['id']

    def get_code_by_id(self, table, id):
        return self.connection.execute(f'select code from {table} where id = {id}').fetchone()['code']

    def count_table(self, table, id):
        return self.connection.execute(f"SELECT count(*) as count FROM {table} where id = '{id}'").fetchone()['count']

    def insert_table(self, table, dic):
        for d in dic:
            if self.count_table(table, d['id']) == '1':
                self.update_row(table, d)
            else:
                self.insert_row(table, d)

    def insert_row(self, table, row):
        def _insert(obj):
            columns = ', '.join(obj.keys())
            placeholders = ':' + ', :'.join(obj.keys())
            query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
            self.connection.execute(query, obj)
            self.connection.commit()
        if isinstance(row, dict):
            _insert(row)
        elif isinstance(row, list):
            for d in row:
                _insert(d)

    def update_row(self, table, row):
        def _update(obj):
            placeholders = ', '.join([f'{key}=:{key}' for key in obj.keys()])
            query = f"UPDATE {table} SET {placeholders} WHERE id = '{obj['id']}'"
            self.connection.execute(query, obj)
            self.connection.commit()
        if isinstance(row, dict):
            _update(row)
        elif isinstance(row, list):
            for d in row:
                _update(d)

    def delete_row(self, table, id):
        self.connection.execute(f'delete from {table} where id = {id}')
        self.connection.commit()

    # product
    # ################################################################
    def get_product_by_code(self, code):
        return self.connection.execute(f"select id, name, sell_price, price_range, buy_price from product where code = '{code}'").fetchone()

    def query_all_product(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, name, class, type, source, quantity, buy_price, sell_price from product"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')
            if 'class' in filter:
                filter_cmd.append(f'class =:class')
            if 'type' in filter:
                filter_cmd.append(f'type =:type')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()


    # ################################################################

    # customer
    # ################################################################

    def get_customer_id_by_name(self, name):
        return self.connection.execute(f"select id from customer where name = '{name}'").fetchone()['id']

    def get_customer_name_by_id(self, id):
        return self.connection.execute(f"select name from customer where id = {id}").fetchone()['name']

    def get_customer_phone_by_name(self, name):
        return self.connection.execute(f"select phone from customer where name = '{name}'").fetchone()['phone']

    def query_all_customer(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, name, phone, balance from customer"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    # ################################################################

    #supplier
    # #################################################################
    def get_supplier_phone_by_name(self, name):
        return self.connection.execute(f"select phone from supplier where name = '{name}'").fetchone()['phone']

    def get_supplier_name_by_id(self, id):
        return self.connection.execute(f"select name from supplier where id = {id}").fetchone()['name']

    def get_supplier_id_by_name(self, name):
        return self.connection.execute(f"select id from supplier where name = '{name}'").fetchone()['id']

    def query_all_supplier(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, name, phone, balance from supplier"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'name' in filter:
                filter['name'] = f'%{filter["name"]}%'
                filter_cmd.append(f'name like :name')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    # ######################################################################


    def query_all_bill_sell(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, c_id, date, total, ispaid from bill_sell"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'c_id' in filter:
                filter_cmd.append(f'c_id =:c_id')

            if 'date_from' in filter:
                if 'date_to' in filter:
                    filter_cmd.append(f'date between :date_from and :date_to')
                else:
                    filter_cmd.append(f'date = :date_from')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()


    def query_all_bill_buy(self, filter: dict, limit1, limit2):
        sql_cmd = "SELECT id, code, s_id, date, total, ispaid from bill_buy"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 's_id' in filter:
                filter_cmd.append(f's_id =:s_id')

            if 'date_from' in filter:
                if 'date_to' in filter:
                    filter_cmd.append(f'date between :date_from and :date_to')
                else:
                    filter_cmd.append(f'date = :date_from')

            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    def get_order_bill(self, table, b_id):
        return self.connection.execute(f"select * FROM {table} WHERE b_id = {b_id}").fetchall()
