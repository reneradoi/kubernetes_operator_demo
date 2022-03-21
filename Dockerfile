FROM python:3.8

ADD database_table_operator.py /src/database_table_operator.py

RUN pip install kopf \
    && pip install kubernetes \
    && pip install psycopg2-binary

CMD kopf run --namespace=default /src/database_table_operator.py