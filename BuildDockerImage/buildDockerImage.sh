#!/bin/bash
cd /scratch/eir17846/PycharmProjects/diamond-xas-website
git pull

# RHEL8 based
podman build --format docker -f ./BuildDockerImage/dockerRhel8Djongo.yaml . -t gcr.io/diamond-privreg/xas-database/k8s-xas-database:rhel8
podman push gcr.io/diamond-privreg/xas-database/k8s-xas-database:rhel8

# RHEL7 based
podman build --format docker -f ./BuildDockerImage/dockerCentos7Djongo.yaml . -t gcr.io/diamond-privreg/conexs/k8conexs:latest
podman push gcr.io/diamond-privreg/xas-database/k8s-xas-database:latest