# Kubernetes Operator Demo

Demo setup to showcase Kubernetes operator based on Python Kopf Framework. The operator handles custom resources which 
are database table definitions and interacts with a locally deployed PostgreSQL database.

## Scope

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

Empty database _demodb_ is now available.

### Setup Python and Demo Repository
The Kubernetes operator will be developed with Python, thus make sure you have Python3 installed:
```
$ which python3
/usr/bin/python3

$ which pip3
/usr/bin/pip3
```

Clone this repository into your local Linux (e.g. WSL2 Ubuntu):
```
$ git clone https://codehub.sva.de/Rene.Radoi/kubernetes_operator_demo.git
Cloning into 'kubernetes_operator_demo'...
[...]

$ cd kubernetes_operator_demo/
$ ls req*
requirements

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

$ kubectl apply -f cr.yaml
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
- if a column was added: connect to the database and update the table structure
- update the status in the resource

*on delete*
- connect to our database
- drop the table

### Run The Operator
To run the Python program locally, no build infrastructure is needed. Just start the program from command line and watch 
it's output. Right after startup, it will handle the custom resource we've added to Kubernetes earlier:

```
$ kopf run database-table-operator.py --namespace=default
[2022-03-18 12:12:40,130] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2022-03-18 12:12:40,136] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2022-03-18 12:12:40,136] kopf._core.engines.a [INFO    ] Initial authentication has finished.
[2022-03-18 12:12:40,533] root                 [INFO    ] Create handler invoked by custom resource website-users. Creating database table.
[2022-03-18 12:12:40,534] kopf.objects         [INFO    ] [default/website-users] Handler 'create_handler' succeeded.
[2022-03-18 12:12:40,534] kopf.objects         [INFO    ] [default/website-users] Creation is processed: 1 succeeded; 0 failed.
```

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
