from sqlcipher3 import dbapi2 as sqlite

db = None


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        value = row[idx]
        key = col[0]
        if isinstance(value, int):
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
        return self.connection.execute(f"select max(id)+1 as seq from {table}").fetchone()['seq']

    def query_row(self, table, id):
        return self.connection.execute(f"select * from {table} where id = {id}").fetchone()

    def insert_row(self, table, row):
        cursor = self.connection.cursor()
        columns = ', '.join(row.keys())
        placeholders = ':' + ', :'.join(row.keys())
        query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        cursor.execute(query, row)
        self.connection.commit()

    def update_row(self, table, row, id):
        placeholders = ', '.join([f'{key}=:{key}' for key in row.keys()])
        query = f'UPDATE {table} SET {placeholders} WHERE id={id}'
        self.connection.execute(query, row)
        self.connection.commit()

    def delete_row(self, table, id):
        self.connection.execute(f'delete from {table} where id = {id}')
        self.connection.commit()

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






    def get_medicine_by_code(self, code):
        return self.connection.execute('SELECT * from medicine WHERE code = ?', (code,)).fetchone()

    def query_medicine_by_ids(self, ids, simple=False):
        if simple:
            sql_cmd = (
                "SELECT id, name from medicine"
                f"WHERE id IN ({','.join(['?'] * len(ids))})"
            )
        else:
            sql_cmd = f"SELECT * from medicine WHERE id IN ({','.join(['?'] * len(ids))})"
        return self.connection.execute(sql_cmd, ids).fetchall()


    # bill sell methods
    def get_bills_next_id(self):
        return self.connection.execute("select seq+1 as seq from sqlite_sequence where name = 'bill_sell'").fetchone()['seq']

    def get_cname(self):
        return {e['id']: e['name'] for e in self.connection.execute('select id, name from customer').fetchall()}

    def get_cphone(self, name):
        return self.connection.execute('select phone from customer where name = ?', (name,)).fetchone()
    # CREATE VIEW order_bill as SELECT order.m_id, medicine.name, medicine.unit, order.amount, medicine.sell_price, order.amount * medicine.sell_price as total, order.discount, total - order.discount as final FROM medicine, order
