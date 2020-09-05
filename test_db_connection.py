from database_lib import db_connection

connection = db_connection()

sql = "SELECT to_regclass('public.announcement')"

cursor = connection.cursor()
cursor.execute(sql)
result = cursor.fetchone()
if result is not None:
    print('Connection successful')
