#!/bin/bash
apk add --update --no-cache openssh
pip3 install -e /srv/jupyterhub
pip3 install PyJWT==1.7.1
export MULTIPLE_INSTANCES=false
HOSTNAME=$(hostname -s)
DIR=${HOSTNAME:11:8}
mkdir -p ${JUPYTERHUB_LOG_BASE_PATH}/${DIR}
JUPYTERHUB_LOG_PATH=${JUPYTERHUB_LOG_BASE_PATH}/${DIR}/${HOSTNAME}.log
export UPDATE_MEMORY_LOG=true
su jupyterhub -c "jupyterhub -f ${JUPYTERHUB_CONFIG_PATH}" >> ${JUPYTERHUB_LOG_PATH} 2>&1
# while true; do sleep 30; done;
