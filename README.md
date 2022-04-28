# Kubernetes Operator Demo

Demo setup to showcase Kubernetes operator based on Python Kopf Framework. The operator handles custom resources which 
are database table definitions and interacts with a locally deployed PostgreSQL database.

Kopf is an open source project, originally being developed at Zalando, now taken care of by the community at 
https://github.com/nolar/kopf. Further information can be found here: https://kopf.readthedocs.io/en/stable/.

## Scope

```
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Kubernetes                                                                                                          +
+                                                                                                                     +
+                                                                      +-----------------------------------+          +
+       +-------------------------+                                    | PostgreSQL Database               |          +
+       | Custom Resource         |                                    |                                   |          +
+       |                         |                                    | ##############################    |          +
+       | Name: my-table          |                                    | # my-table                   #    |          +
+       | Spec:                   |                                    | #                            #    |          +
+       |   column1: integer      |                                    | # column1  column2 column3   #    |          +
+       |   column2: integer      |                                    | # ------------------------   #    |          +
+       |   column3: varchar(20)  |                                    | # ...      ...     ...       #    |          +
+       |   ...                   |                                    | # ...      ...     ...       #    |          +
+       +-------------------------+                                    | ##############################    |          +
+                  ^                                                   |                                   |          +
+                  |                                                   |                                   |          +
+                  |                                                   +-----------------------------------+          +
+                watch                                                                  ^                             +
+                  |                                                                    |                             +
+                  |                +---------------------------+           CREATE / UPDATE / DROP TABLE              +
+                  |                |                           |                       |                             +
+                  -----------------|  Database Table Operator  |------------------------                             +
+                                   |                           |                                                     +
+                                   +---------------------------+                                                     +
+                                                                                                                     +
+                                                                                                                     +
+                                                                                                                     +
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
```

## Demo Setup
### Prerequisites
- docker
- minikube: https://minikube.sigs.k8s.io/docs/start/
- helm 3.2.0+

### Setup PostgreSQL
This demo uses a local PostgreSQL database installed via Bitnami Helm Chart. For detailed information please refer to 
https://github.com/bitnami/charts/tree/master/bitnami/postgresql.

In short:
```
$ helm repo add bitnami https://charts.bitnami.com/bitnami
"bitnami" has been added to your repositories

$ helm install postgresql bitnami/postgresql --set=auth.database=demodb --set=auth.username=demouser --set=auth.password=demopw
[...]

$ kubectl get pods
NAME           READY   STATUS    RESTARTS   AGE
postgresql-0   1/1     Running   0          2m50s

$ kubectl get pvc
NAME                STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-postgresql-0   Bound    pvc-bdd6f64d-37b4-4344-bb27-acbab1b1ee06   8Gi        RWO            standard       4m48s

$ kubectl get secret --namespace default postgresql -o jsonpath="{.data.password}" | base64 --decode
demopw

$ kubectl exec -it postgresql-0 -- bash
I have no name!@postgresql-0:/$

$ psql -h localhost -U demouser demodb
Password for user demouser:

demodb=> \d
Did not find any relations.
```

Empty database _demodb_ is now available. Let's create port forwarding from our localhost to the pod, in order to connect
to the database within the pod. Run the task in the background for continuing in this shell:

```
$ kubectl port-forward pod/postgresql-0 5432:5432
Forwarding from 127.0.0.1:5432 -> 5432
Forwarding from [::1]:5432 -> 5432

[CTRL+Z]
[1]+  Stopped                 kubectl port-forward pod/postgresql-0 5432:5432
$ bg
[1]+ kubectl port-forward pod/postgresql-0 5432:5432 &
```

### Setup Python and Demo Repository
The Kubernetes operator is based on Python, thus make sure you have Python3 installed:
```
$ which python3
/usr/bin/python3

$ which pip3
/usr/bin/pip3
```

Clone this repository into your local Linux (e.g. WSL2 Ubuntu) and install the required Python packages:
```
$ git clone https://codehub.sva.de/Rene.Radoi/kubernetes_operator_demo.git
Cloning into 'kubernetes_operator_demo'...
[...]

$ cd kubernetes_operator_demo/
$ cat requirements
kopf
kubernetes
psycopg2-binary

$ pip3 install -r requirements
[...]
```

## Development
### Kubernetes Resources
Let's create a custom resource definition. This configures how our database table definitions in Kubernetes will look like.

```
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databasetables.kopf.demo
spec:
  scope: Namespaced
  group: kopf.demo
  names:
    kind: DatabaseTable
    plural: databasetables
    singular: databasetable
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
              required: ["tableName","columns","primaryKey"]
              x-kubernetes-preserve-unknown-fields: true
            status:
              type: object
              x-kubernetes-preserve-unknown-fields: true
```

Next step is to create our very first database table definition:
```
apiVersion: kopf.demo/v1
kind: DatabaseTable
metadata:
  name: website-users
spec:
  tableName: WEBSITE_USERS
  columns:
    - USER_ID: integer
    - USER_NAME: varchar(50)
    - USER_EMAIL: varchar(100)
    - SIGNUP_DATE: date
    - LAST_LOGIN: timestamp
  primaryKey: USER_ID
```

These objects will now be applied to Kubernetes:
```
$ kubectl apply -f crd.yaml
customresourcedefinition.apiextensions.k8s.io/databasetables.kopf.demo created

$ kubectl apply -f example-cr.yaml
databasetable.kopf.demo/website-users created

$ kubectl get DatabaseTables
NAME            AGE
website-users   13s
```

### Operator Functionality
We want our operator to handle the Kubernetes resources for us. Thus we define what to do when a custom resource is added,
updated or removed:

*on create*
- connect to our database
- create the table according to the specification in the resource
- update the status in the resource

*on update*
- check the diff
- if a column was removed or changed: log an error and abort the update
- if a column was added, table name or primary key was changed: connect to the database and update the table structure
- update the status in the resource

*on delete*
- connect to our database
- drop the table

### Run The Operator
To run the Python program locally, no build infrastructure is needed. Just start the program from command line and watch 
it's output. Right after startup, it will handle the custom resource we've added to Kubernetes earlier:

```
$ kopf run database_table_operator.py --namespace=default --verbose
[2022-03-18 12:12:40,130] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2022-03-18 12:12:40,136] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2022-03-18 12:12:40,136] kopf._core.engines.a [INFO    ] Initial authentication has finished.
[2022-03-18 12:12:40,533] root                 [INFO    ] Create handler invoked by custom resource website-users. Creating database table.
[2022-03-18 12:12:40,533] root                 [DEBUG   ] SQL statement: CREATE TABLE WEBSITE_USERS (USER_ID integer, USER_NAME varchar(50), USER_EMAIL varchar(100), SIGNUP_DATE date, LAST_LOGIN timestamp, PRIMARY KEY (USER_ID));
[2022-03-18 12:12:40,534] kopf.objects         [INFO    ] [default/website-users] Handler 'create_handler' succeeded.
[2022-03-18 12:12:40,534] kopf.objects         [INFO    ] [default/website-users] Creation is processed: 1 succeeded; 0 failed.
```

A quick look to the database confirms that the table has been created:
```
$ psql -h localhost -U demouser demodb
[...]
demodb=> \d
             List of relations
 Schema |     Name      | Type  |  Owner
--------+---------------+-------+----------
 public | website_users | table | demouser
(1 row)
```
## Deployment
*The following topics are hints and recommendations for using an operator in production. They are not mandatory for this demo though.*

### Namespacing
In theory it is possible to run the operator and the resources with cluster-wide scope, but this is not recommended in 
general. Please use one or several namespaces in the Kubernetes cluster to separate concerns. The example files in this 
repo are all namespaced, though the namespace in your production stage should probably not be *default* like in this demo.  

### Docker Image
Running the operator like shown above should only be done for development or testing purposes, not for production use. 
Instead package the operator into a docker image and ship it to production (or other stages). The image doesn't even
require a Linux distribution, just Python.

Here's an example for building the image, you can also find it as `Dockerfile` in the source code:
```
FROM python:3.8                                                                     ---[1]
ENV WATCH_NAMESPACE=default                                                         ---[2]

ADD database_table_operator.py /src/database_table_operator.py                      ---[3]

RUN pip install kopf \                                                              ---[4]
    && pip install kubernetes \
    && pip install psycopg2-binary \
    && groupadd -g 1000 operator \                                                  ---[5]
    && useradd -g operator -u 1000 -m operator

USER operator                                                                       ---[6]

CMD kopf run --namespace=${WATCH_NAMESPACE} /src/database_table_operator.py         ---[7]
```

The steps explained:
- [1] - download Python from docker registry
- [2] - add environment variable to configure namespace
- [3] - add python program to directory */src* of the image
- [4] - install the required python packages via pip (could also be done with the requirements file, shown here for understanding)
- [5] - add a non-root user/group to run the image (security!)
- [6] - switch to non-root user
- [7] - start the operator in the configured (or default) namespace

### Service Account and Roles/Permissions
This demo uses minikube for showcasing, no need to use a service account or specific permissions for this demo. But when 
you deploy to a non-local Kubernetes cluster, you will surely need a service account and the respective permissions to
watch and update resources.

Our demo operator would require the following permissions:
- create, list, watch, patch resources of type *databasetables*
- create events
- get secrets

An example for setting up the account, roles and rolebindings can be found in the file `service-account.yaml` in this repo.

### Don't mess with the responsibilities
Finally, a general remark: If your operator handles the database tables, don't create, update or drop them
otherwise anymore! This would result in errors while trying to apply changes to the resources, because via finalizers 
Kubernetes is waiting for the operator to acknowledge the action. 

If you cannot guarantee single responsibility, add extensive error handling to your operator. 

And just for information, with this dirty hack, you can solve deadlock situations: 
`kubectl patch databasetable website-users -p '{"metadata": {"finalizers": []}}' --type merge`

## Tear Down Demo Setup
Remove PostgreSQL database and persistent volume:
```
$ helm delete postgresql
release "postgresql" uninstalled

$ kubectl get pvc
NAME                STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-postgresql-0   Bound    pvc-bdd6f64d-37b4-4344-bb27-acbab1b1ee06   8Gi        RWO            standard       35m

$ kubectl delete pvc data-postgresql-0
persistentvolumeclaim "data-postgresql-0" deleted
```

If the port forwarding was running in the background, don't forget to remove that as well: `pkill -f "port-forward"`
