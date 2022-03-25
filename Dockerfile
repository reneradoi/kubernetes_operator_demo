FROM python:3.8
ENV WATCH_NAMESPACE=default

ADD database_table_operator.py /src/database_table_operator.py

RUN pip install kopf \
    && pip install kubernetes \
    && pip install psycopg2-binary \
    && groupadd -g 1000 operator \
    && useradd -g operator -u 1000 -m operator

USER operator

CMD kopf run --namespace=${WATCH_NAMESPACE} /src/database_table_operator.py