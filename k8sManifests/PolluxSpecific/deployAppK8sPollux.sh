# start with secrets - skip if already exist
cd /scratch/eir17846/PycharmProjects/diamond-xas-website
module load pollux && kubectl get pods
kubeseal <mongodb_auth_secret.yaml >k8s_mongo_sealedsecret.yaml -o yaml
kubeseal <xasdb_auth_secret.yaml >k8s_xasdb_sealedsecret.yaml -o yaml
cp k8s_mongo_sealedsecret.yaml k8sManifests/PolluxSpecific/k8s_mongo_sealedsecret.yaml
cp k8s_xasdb_sealedsecret.yaml k8sManifests/PolluxSpecific/k8s_xasdb_sealedsecret.yaml

# deploy sealed secrets
cd /scratch/eir17846/PycharmProjects/diamond-xas-website/k8sManifests
kubectl apply -f PolluxSpecific/k8s_mongo_sealedsecret.yaml
kubectl apply -f PolluxSpecific/k8s_xasdb_sealedsecret.yaml

# deploy configmaps
kubectl apply -f PolluxSpecific/k8s_mongo_configmap.yaml
kubectl apply -f PolluxSpecific/k8s_xasdb_configmap.yaml

#deploy cronjobs
kubectl apply -f k8s_mongo_restore_crongob.yaml
kubectl apply -f k8s_mongo_backup_crongob.yaml

#finally deploy django app
kubectl apply -f PolluxSpecific/k8s_xasdb_deployment.yaml

#deploy mongo db
kubectl apply -f k8s_mongo_deployment.yaml

#deploy mongo express if needed
kubectl apply -f k8s_mongo_express.yaml
