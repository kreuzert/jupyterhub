#!/bin/sh
jupyterhub -f ${JUPYTERHUB_CONFIG_PATH} >> ${JUPYTERHUB_LOG_PATH} 2>&1
