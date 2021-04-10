#!/bin/bash
HOSTNAME=$(hostname -s)
JUPYTERHUB_LOG_PATH=${JUPYTERHUB_LOG_BASE_PATH}/jupyterhub.log
su jupyterhub -c "jupyterhub -f ${JUPYTERHUB_CONFIG_PATH}" >> ${JUPYTERHUB_LOG_PATH} 2>&1
