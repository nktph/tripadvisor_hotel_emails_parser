import sqlite3

path_db = "database.db"
# Преобразование полученного списка в словарь
def dict_factory(cursor, row):
    save_dict = {}

    for idx, col in enumerate(cursor.description):
        save_dict[col[0]] = row[idx]

    return save_dict


# Форматирование запроса без аргументов
def query(sql, parameters: dict):
    if "XXX" not in sql: sql += " XXX "
    values = ", ".join([
        f"{item} = ?" for item in parameters
    ])
    sql = sql.replace("XXX", values)

    return sql, list(parameters.values())


# Форматирование запроса с аргументами
def query_args(sql, parameters: dict):
    sql = f"{sql} WHERE "

    sql += " AND ".join([
        f"{item} = ?" for item in parameters
    ])

    return sql, list(parameters.values())


def register_hotel(name, email):
    with sqlite3.connect(path_db) as con:
        con.row_factory = dict_factory
        con.execute("INSERT INTO hotels("
                    "name, email) "
                    "VALUES (?,?)", [name, email])
        con.commit()


# Получение пользователя из БД
def get_hotel(**kwargs):
    with sqlite3.connect(path_db) as con:
        con.row_factory = dict_factory
        queryy = "SELECT * FROM hotels"
        queryy, params = query_args(queryy, kwargs)
        return con.execute(queryy, params).fetchone()


def create_db():
    with sqlite3.connect(path_db) as con:
        con.row_factory = dict_factory

        # Пользователи
        if len(con.execute("PRAGMA table_info(hotels)").fetchall()) == 16:
            print("database was found (hotels)")
        else:
            con.execute("CREATE TABLE hotels("
                        "increment INTEGER PRIMARY KEY AUTOINCREMENT,"
                        "name TEXT UNIQUE,"
                        "email TEXT)")

            print("database was not found, creating...")