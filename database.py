from sqlite3 import dbapi2 as sqlite
from functools import lru_cache
import re


db = None

re_query = re.compile("^select .* from (.*)$", re.IGNORECASE)
re_limit = re.compile(" limit .*$", re.IGNORECASE)


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
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.connection.row_factory = _dict_factory

    @staticmethod
    def open_database():
        global db
        db = Database('j_shop.db')

    def change_user_pass(self, username, password):
        self.connection.execute('UPDATE users SET pass = ? WHERE users.name = ?', (password, username))
        self.connection.commit()

    def get_users(self):
        return self.connection.execute("SELECT * from users").fetchall()

    def is_user(self, username):
        return self.connection.execute("select pass, permission from users where name = ?", (username,)).fetchone()

    def count_row(self, table, r):
        if r == 1:
            return self.connection.execute(f'select count(*) as count from {table}').fetchone()['count']
        else:
            return self.connection.execute(f'select count(*) as count from {table} where code = ?', (r,)).fetchone()[
                'count']

    def get_next_id(self, table):
        if self.connection.execute(f"select max(id)+1 as seq from {table}").fetchone()['seq'] == '':
            return 1
        return self.connection.execute(f"select max(id)+1 as seq from {table}").fetchone()['seq']

    def query_row(self, table, id):
        return self.connection.execute(f"select * from {table} where id = ?", (id,)).fetchone()

    def query_csp(self, table):
        return {e['id']: e['name'] for e in self.connection.execute(f'select id, name from {table}').fetchall()}

    def get_id_by_code(self, table, code) -> str:
        return self.connection.execute(f"select id from {table} where code = ?", (code, )).fetchone()['id']

    def get_code_by_id(self, table, id):
        return self.connection.execute(f'select code from {table} where id = ?', (id, )).fetchone()['code']

    def count_table(self, table, id):
        return self.connection.execute(f"SELECT count(*) as count FROM {table} where id = ?", (id, )).fetchone()['count']

    def get_earnings(self, now, month):
        earn_sale = self.connection.execute(
            "SELECT sum((sell_order.total - sell_order.discount) - sell_order.quantity * product.buy_price) as earn_sale "
            "FROM sell_order, product WHERE sell_order.p_id = product.id and"
            " b_id in (SELECT id FROM bill_sell WHERE date <= ? and date > ?)", (now, month)
        ).fetchone()['earn_sale']

        naf = self.connection.execute(
            "SELECT value + (value_t / do_tr) as naf FROM fund_movement WHERE type = 'نفقات' and date <= ? and date > ?", (now, month)
        ).fetchone()['naf']

        return float(earn_sale) - float(naf)

    def get_sales(self, now, month):
        return self.connection.execute(
            "SELECT sum(total - discount) as sales FROM bill_sell WHERE date <= ? and date > ?", (now, month)).fetchone()['sales']

    def get_purchases(self, now, month):
        return self.connection.execute(
            "SELECT sum(total - discount) as purchases FROM bill_buy WHERE date <= ? and date > ?", (now, month)).fetchone()['purchases']

    def get_capital(self, with_box, do_tr) -> float:
        pro_capital = self.connection.execute("SELECT sum(quantity * buy_price) as pro_capital FROM product").fetchone()[
                'pro_capital']
        if pro_capital == '':
            pro_capital = '0'
        if do_tr == 0:
            box = self.connection.execute("SELECT dollar as box FROM box").fetchone()['box']
        else:
            box = self.connection.execute("SELECT dollar + (turky / ?) as box FROM box", (do_tr,)).fetchone()['box']
        if with_box:
            return float(box if box else '0') + float(pro_capital)
        else:
            return float(pro_capital)

    def insert_table(self, table, dic, fk):
        new_ids = [int(d['id']) for d in dic]
        placeholders = ", ".join("?" * len(new_ids))
        del_ids = self.connection.execute(f"SELECT id FROM {table} WHERE b_id = ? and id not in ({placeholders})",
                                          tuple([fk, *new_ids])).fetchall()
        for d in dic:
            if self.count_table(table, d['id']) == '1':
                self.update_row(table, d)
            else:
                self.insert_row(table, d)
        for d in del_ids:
            self.delete_row(table, d['id'])

    def insert_users(self, lis):
        new_ids = [str(d['id']) for d in lis]
        placeholders = ", ".join("?" * len(new_ids))
        del_ids = self.connection.execute(f"SELECT id FROM users WHERE id not in ({placeholders})", tuple(new_ids)).fetchall()
        for d in lis:
            if self.count_table("users", d['id']) == '1':
                self.update_row("users", d)
            else:
                self.insert_row("users", d)
        for d in del_ids:
            self.delete_row("users", d['id'])

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
            placeholders = ', '.join([f'{key}=?' for key in obj.keys()])
            query = f"UPDATE {table} SET {placeholders} WHERE id = ?"
            li = list(obj.values())
            li.append(obj['id'])
            self.connection.execute(query, tuple(li))
            self.connection.commit()

        if isinstance(row, dict):
            _update(row)
        elif isinstance(row, list):
            for d in row:
                _update(d)

    def delete_row(self, table, id):
        self.connection.execute(f'delete from {table} where id = ?', (id,))
        self.connection.commit()

    # product
    # ################################################################
    def get_product_by_code(self, code):
        return self.connection.execute(
            f"select id, name, quantity, sell_price, sell_price_wh, price_range, buy_price from product where code = ?",
            (code,)).fetchone()

    def get_product_like_code(self, code) -> list:
        code = f'%{code}%'
        return self.connection.execute(f"select * from product where code like ?", (code,)).fetchall()

    def get_query_count(self, query: str, filter: dict = {}):
        @lru_cache(128)
        def _get_query_count(frozen_filter: frozenset):
            g = re_query.match(query).group(1)
            l = re_limit.sub('', g)
            new_query = f"select count(*) as count from {l}"
            return self.connection.execute(new_query, dict(frozen_filter)).fetchone()['count']
        return _get_query_count(frozenset(filter.items()))

    def clear_query_count_cache(self):
        self.get_query_count.cache_clear()

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
            count = self.get_query_count(sql_cmd, filter)
            return count, self.connection.execute(sql_cmd, filter).fetchall()
        else:
            count = self.get_query_count(sql_cmd)
            sql_cmd += f' limit {limit1}, {limit2}'
            return count, self.connection.execute(sql_cmd).fetchall()

    # ################################################################

    # customer and suppliers
    # ################################################################

    def get_id_by_name(self, table, name):
        return self.connection.execute(f"select id from {table} where name = ?", (name,)).fetchone()['id']

    def get_name_by_id(self, table, id):
        return self.connection.execute(f"select name from {table} where id = ?", (id,)).fetchone()['name']

    def get_phone_by_name(self, table, name):
        return self.connection.execute(f"select phone from {table} where name = ?", (name,)).fetchone()['phone']

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
            count = self.get_query_count(sql_cmd, filter)
            return count, self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' limit {limit1}, {limit2}'
            count = self.get_query_count(sql_cmd)
            return count, self.connection.execute(sql_cmd).fetchall()

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
            sql_cmd += f' ORDER by date DESC limit {limit1}, {limit2}'
            count = self.get_query_count(sql_cmd, filter)
            return count, self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' ORDER by date DESC limit {limit1}, {limit2}'
            count = self.get_query_count(sql_cmd)
            return count, self.connection.execute(sql_cmd).fetchall()

    def get_balance(self, type_fm, owner):
        if type_fm == "دفعة من زبون":
            return self.connection.execute("SELECT balance FROM customer WHERE id = ?", (owner,)).fetchone()['balance']
        else:
            return self.connection.execute("SELECT balance FROM supplier WHERE id = ?", (owner,)).fetchone()['balance']

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
            sql_cmd += f' ORDER by date DESC limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd, filter).fetchall()
        else:
            sql_cmd += f' ORDER by date DESC limit {limit1}, {limit2}'
            return self.connection.execute(sql_cmd).fetchall()

    def get_order_bill(self, table, b_id):
        return self.connection.execute(f"select * FROM {table} WHERE b_id = ?", (b_id,)).fetchall()

    def get_noti_pro1(self):
        return self.connection.execute(
            f"SELECT code, name, quantity FROM product WHERE quantity <= less_quantity").fetchall()

    def get_noti_pro2(self):
        return self.connection.execute(f"SELECT code, name, quantity FROM product WHERE quantity = 0").fetchall()

    def get_noti_cus(self, table):
        return self.connection.execute(
            f"SELECT code, name, range_balance FROM {table} WHERE balance >= range_balance").fetchall()

    def get_box(self):
        return self.connection.execute("SELECT * FROM box").fetchone()

    def exchange_dollar_turky(self, to, do, tu):
        if to == 'do_tu':
            self.connection.execute("UPDATE box SET dollar = dollar - ?, turky = turky + ?", (do, tu))
        else:
            self.connection.execute("UPDATE box SET dollar = dollar + ?, turky = turky - ?", (do, tu))
        self.connection.commit()
