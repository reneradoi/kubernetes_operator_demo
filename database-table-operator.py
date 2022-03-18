import kopf
import logging
import kubernetes
import psycopg2


@kopf.on.create('databasetable')
def create_handler(spec, name, patch, **kwargs):
    logging.info(f"Create handler invoked by custom resource {name}. Creating database table.")

    table_name = spec.get('tableName')
    if table_name is None:
        raise kopf.PermanentError("Config item 'tableName' is missing in spec.")
    logging.info(f"table name: {table_name}")

    table_columns = spec.get('columns')
    if table_columns is None:
        raise kopf.PermanentError("Config item 'columns' is missing in spec.")
    logging.info(f"table columns: {table_columns}")

    table_keys = spec.get('primaryKey').split()
    logging.info(f"table primary key: {table_keys}")

    conn = get_database_connection()


@kopf.on.update('databasetable')
def update_handler(spec, name, diff, patch, **kwargs):
    logging.info(f"Update handler invoked by custom resource {name}. Updating database table.")


@kopf.on.delete('databasetable')
def delete_handler(name, **kwargs):
    logging.info(f"Delete handler invoked by custom resource {name}. Deleting database table.")


def get_database_connection():
    pass