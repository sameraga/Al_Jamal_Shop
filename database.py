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
        new_ids = [int(d['id']) for d in dic]
        placeholders = ", ".join("?" * len(new_ids))
        del_ids = self.connection.execute(f"SELECT id FROM {table} WHERE b_id = {dic[0]['b_id']} and id not in ({placeholders})", tuple(new_ids)).fetchall()
        for d in dic:
            if self.count_table(table, d['id']) == '1':
                self.update_row(table, d)
            else:
                self.insert_row(table, d)
        for d in del_ids:
            self.delete_row(table, d['id'])

    def insert_row(self, table, row):
        def _insert(obj):
            columns = ', '.join(obj.keys())
            placeholders = ':' + ', :'.join(obj.keys())
            query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
            self.connection.execute(query, obj)
            self.connection.commit()

        if isinstance(row, dict):
            if table == "bill_sell":
                if not row['ispaid']:
                    b = float(row['total']) - float(row['discount'])
                    self.connection.execute(f"UPDATE customer set balance = balance + {b} WHERE customer.id = {row['c_id']}")
            elif table == "bill_buy":
                if not row['ispaid']:
                    b = float(row['total']) - float(row['discount'])
                    self.connection.execute(f"UPDATE supplier set balance = balance + {b} WHERE supplier.id = {row['s_id']}")
            elif table == "buy_order":
                self.connection.execute(f"UPDATE product SET quantity = quantity + {row['quantity']} WHERE id = {row['p_id']}")
            elif table == "sell_order":
                self.connection.execute(f"UPDATE product SET quantity = quantity - {row['quantity']} WHERE id = {row['p_id']}")
            elif table == "fund_movement":
                if row['type'] == "دفعة من زبون":
                    self.connection.execute(f"UPDATE customer SET balance = balance - {row['value']} WHERE id = {row['owner']}")
                elif row['type'] == "دفعة إلى مورد":
                    self.connection.execute(f"UPDATE supplier SET balance = balance - {row['value']} WHERE id = {row['owner']}")
            _insert(row)
        elif isinstance(row, list):
            for d in row:
                _insert(d)

    def update_row(self, table, row):
        def _update(obj):
            placeholders = ', '.join([f'{key}=:{key}' for key in obj.keys()])
            query = f"UPDATE {table} SET {placeholders} WHERE id = '{obj['id']}'"
            if table == "bill_sell":
                if not obj['ispaid']:
                    b = float(obj['total']) - float(obj['discount'])
                    self.connection.execute(f"UPDATE customer set balance = balance + {b} WHERE customer.id = {obj['c_id']}")
            elif table == "bill_buy":
                if not obj['ispaid']:
                    b = float(obj['total']) - float(obj['discount'])
                    self.connection.execute(f"UPDATE supplier set balance = balance + {b} WHERE supplier.id = {obj['s_id']}")
            elif table == "buy_order":
                qu = self.connection.execute(f"SELECT quantity FROM buy_order WHERE id = {obj['id']}").fetchone()['quantity']
                self.connection.execute(f"UPDATE product SET quantity = quantity - {qu} + {obj['quantity']} WHERE id = {obj['p_id']}")
            elif table == "sell_order":
                qu = self.connection.execute(f"SELECT quantity FROM sell_order WHERE id = {obj['id']}").fetchone()['quantity']
                self.connection.execute(f"UPDATE product SET quantity = quantity + {qu} - {obj['quantity']} WHERE id = {obj['p_id']}")
            elif table == "fund_movement":
                qu = self.connection.execute(f"SELECT value FROM fund_movement WHERE id = {obj['id']}").fetchone()['value']
                if obj['type'] == "دفعة من زبون":
                    self.connection.execute(f"UPDATE customer SET balance = balance + {qu} - {obj['value']} WHERE id = {obj['owner']}")
                elif obj['type'] == "دفعة إلى مورد":
                    self.connection.execute(f"UPDATE supplier SET balance = balance + {qu} - {obj['value']} WHERE id = {obj['owner']}")
            self.connection.execute(query, obj)
            self.connection.commit()
        if isinstance(row, dict):
            _update(row)
        elif isinstance(row, list):
            for d in row:
                _update(d)

    def delete_row(self, table, id):
        if table == 'fund_movement':
            fm = self.connection.execute(f"SELECT type, owner, value FROM fund_movement WHERE id = {id}").fetchone()
            if fm['type'] == 'دفعة من زبون':
                self.connection.execute(f"UPDATE customer SET balance = balance + {fm['value']} WHERE id = {fm['owner']}")
            elif fm['type'] == 'دفعة إلى مورد':
                self.connection.execute(f"UPDATE supplier SET balance = balance - {fm['value']} WHERE id = {fm['owner']}")
        self.connection.execute(f'delete from {table} where id = {id}')
        self.connection.commit()

    # product
    # ################################################################
    def get_product_by_code(self, code):
        return self.connection.execute(f"select id, name, quantity, sell_price, price_range, buy_price from product where code = '{code}'").fetchone()

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

    # customer and suppliers
    # ################################################################

    def get_id_by_name(self, table, name):
        return self.connection.execute(f"select id from {table} where name = '{name}'").fetchone()['id']

    def get_name_by_id(self, table, id):
        return self.connection.execute(f"select name from {table} where id = {id}").fetchone()['name']

    def get_phone_by_name(self, table, name):
        return self.connection.execute(f"select phone from {table} where name = '{name}'").fetchone()['phone']

    def query_all_cs(self, table, filter: dict, limit1, limit2):
        sql_cmd = f"SELECT id, code, name, phone, balance from {table}"

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

    def query_all_fm(self, filter: dict, limit1, limit2):
        sql_cmd = f"SELECT * from fund_movement"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'type' in filter:
                filter_cmd.append(f'type = :type')
            if 'owner' in filter:
                filter_cmd.append(f'owner = :owner')
            if 'date_from' in filter:
                if 'date_to' in filter:
                    filter_cmd.append(f'date between :date_from and :date_to')
                else:
                    filter_cmd.append(f'date = :date_from')
            if 'note' in filter:
                filter['note'] = f'%{filter["note"]}%'
                filter_cmd.append(f'note like :note')
            sql_cmd += ' and '.join(filter_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    # ################################################################

    def query_all_bill(self, bill_type, filter: dict, limit1, limit2):
        sql_cmd = f"SELECT * from {bill_type}"

        if filter:
            sql_cmd += " where "
            filter_cmd = []
            if 'code' in filter:
                filter['code'] = f'%{filter["code"]}%'
                filter_cmd.append(f'code like :code')
            if 'c_id' in filter:
                filter_cmd.append(f'c_id =:c_id')
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
