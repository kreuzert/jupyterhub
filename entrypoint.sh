#!/bin/sh
HOSTNAME=$(hostname -s)
JUPYTERHUB_LOG_PATH=${JUPYTERHUB_LOG_BASE_PATH}/${HOSTNAME}.log
jupyterhub -f ${JUPYTERHUB_CONFIG_PATH} >> ${JUPYTERHUB_LOG_PATH} 2>&1
# while true; do sleep 30; done;
