"""The database table operator is a demo Python program showing how to handle events on Kubernetes custom resources,
creating, updating or deleting the respective database table in a local PostgreSQL database."""

import kopf
import logging
import kubernetes
from base64 import b64decode
import psycopg2


@kopf.on.create('databasetable')
def create_handler(spec, name, patch, **kwargs):
    logging.info(f"Create handler invoked by custom resource {name}. Creating database table.")

    table_name, table_keys, table_columns = check_spec(spec)

    """"Put together SQL statement to create the table in the database"""
    create_statement = "CREATE TABLE " + table_name + " ("
    for column in table_columns:
        for column_name, column_type in column.items():
            create_statement = create_statement + column_name + " " + column_type + ", "
    create_statement = create_statement + "PRIMARY KEY (" + table_keys + "));"

    logging.debug(f"SQL statement: {create_statement}")

    try:
        conn, cur = get_database_connection()
        cur.execute(create_statement)
        conn.commit()
        conn.close()
    except Exception as error:
        patch.status['operation'] = "CREATE FAILED"
        raise kopf.TemporaryError(f"Error while creating table {table_name}: {error}")

    patch.status['operation'] = "CREATED"


@kopf.on.update('databasetable')
def update_handler(spec, name, old, new, patch, **kwargs):
    logging.info(f"Update handler invoked by custom resource {name}. Updating database table.")
    table_name, table_keys, table_columns = check_spec(spec)

    try:
        conn, cur = get_database_connection()

        if old['spec'].get('tableName') != table_name:
            logging.info(f"update table name: {table_name}")
            cur.execute(f"ALTER TABLE {old['spec'].get('tableName')} RENAME TO {table_name};")
            conn.commit()

        if old['spec'].get('primaryKey') != table_keys:
            logging.info(f"Update primary key: {table_keys}")
            cur.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {table_name}_pkey, ADD PRIMARY KEY ({table_keys});")
            conn.commit()

        if old['spec'].get('columns') != table_columns:
            logging.info(f"Update columns")
            for column in table_columns:
                if column not in old['spec'].get('columns'):
                    logging.debug(f"Add column {column}")
                    for column_name, column_type in column.items():
                        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                        conn.commit()

            for old_column in old['spec'].get('columns'):
                if old_column not in table_columns:
                    raise kopf.PermanentError(f"Error while updating: Removing column {old_column} is not supported.")

        conn.close()
    except Exception as error:
        patch.status['operation'] = "UPDATE FAILED"
        raise kopf.TemporaryError(f"Error while updating table {table_name}: {error}")

    patch.status['operation'] = "UPDATED"


@kopf.on.delete('databasetable')
def delete_handler(name, spec, patch, **kwargs):
    logging.info(f"Delete handler invoked by custom resource {name}. Deleting database table.")

    table_name = spec.get('tableName')
    try:
        conn, cur = get_database_connection()
        cur.execute(f"DROP TABLE {table_name};")
        conn.commit()
        conn.close()
    except Exception as error:
        patch.status['operation'] = "DELETION FAILED"
        raise kopf.TemporaryError(f"Error while deleting table {table_name}: {error}")


def get_database_connection():
    db_name = "demodb"
    db_user = "demouser"
    db_host = "localhost"
    db_port = "5432"

    """"
    Get database password from Kubernetes secret.
    If running in a Kubernetes pod, the kube.config has to be loaded using kubernetes.config.load_incluster_config(). 
    """
    kubernetes.config.load_config()
    secret = kubernetes.client.CoreV1Api().read_namespaced_secret('postgresql', 'default').data
    db_passwd = b64decode(secret['password']).decode('utf-8')

    conn = psycopg2.connect(
        database=db_name,
        user=db_user,
        password=db_passwd,
        host=db_host,
        port=db_port)

    cur = conn.cursor()

    return conn, cur


def check_spec(spec):
    """Check if spec is valid. Expected items: tableName, columns, primaryKey."""
    table_name = spec.get('tableName')
    if table_name is None:
        raise kopf.PermanentError("Config item 'tableName' is missing in spec.")
    logging.debug(f"table name: {table_name}")

    table_columns = spec.get('columns')
    if table_columns is None:
        raise kopf.PermanentError("Config item 'columns' is missing in spec.")
    logging.debug(f"table columns: {table_columns}")

    table_keys = spec.get('primaryKey')
    if table_keys is None:
        raise kopf.PermanentError("Config item 'primaryKey' is missing in spec.")
    logging.debug(f"table primary key: {table_keys}")

    return table_name, table_keys, table_columns
