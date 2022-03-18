import kopf
import logging
import kubernetes
import psycopg2


@kopf.on.create('databasetable')
def create_handler(spec, name, patch, **kwargs):
    logging.info(f"Create handler invoked by custom resource {name}. Creating database table.")


@kopf.on.update('databasetable')
def update_handler(spec, name, diff, patch, **kwargs):
    logging.info(f"Update handler invoked by custom resource {name}. Updating database table.")


@kopf.on.delete('databasetable')
def delete_handler(name, **kwargs):
    logging.info(f"Delete handler invoked by custom resource {name}. Deleting database table.")