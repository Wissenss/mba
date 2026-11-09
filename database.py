import os
import sqlite3
import environment

def create_connection():
    return sqlite3.connect(environment.DB_PATH)

def read_file_query(path : str):
    name, ext = os.path.splitext(path)

    if ext.lower() != '.sql':
        raise ValueError("the given path is not a sql file")
    
    with open(path, encoding='UTF-8') as file:
        return file.read()

def update_schema():
    con = create_connection()
    cur = con.cursor()
    
    migrations_dir = "./schema"
    
    # create the schema if not found
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Settings';")

    if not cur.fetchone():
        sql = read_file_query(os.path.join(migrations_dir, "000.sql"))
        cur.executescript(sql)

    # check what is the last migration applied

    cur.execute("SELECT value FROM Settings WHERE key = 'db_version';")
    version = cur.fetchone()[0]

    # lookup migrations and apply the pending ones, one by one

    migrations_files = [f for f in os.listdir(migrations_dir) if os.path.isfile(os.path.join(migrations_dir, f))]
    migrations_files.sort()

    for file in migrations_files:
        name, ext = os.path.splitext(file)

        if version < name:
            sql = read_file_query(os.path.join(migrations_dir, file))
            cur.executescript(sql)

            # record the applied migration so it doesn't run again on the next start
            cur.execute("UPDATE Settings SET value = ? WHERE key = 'db_version';", [name])
            con.commit()

            version = name
        
if __name__ == "__main__":
    update_schema()
