# Kubernetes operator demo

Demo setup to showcase Kubernetes operator based on Python Kopf Framework. The operator handles custom resources which are database table definitions and interacts with a locally deployed PostgreSQL database.

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

## Functionality

### on create
- DB Verbindung erzeugen
- Tabelle anlegen
- Status in CR aktualisieren

### on update
- diff überprüfen: Wurde Spalte gelöscht oder geändert: Fehlermeldung ausgeben
- DB Verbindung erzeugen
- neue Spalten hinzufügen
- Status in CR aktualisieren

### on delete
- DB Verbindung erzeugen
- Tabelle löschen
- Status in CR aktualisieren
- 
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
