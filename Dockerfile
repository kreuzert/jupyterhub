# FROM python:3.8.7-alpine3.12
FROM python:3.9.2-alpine3.13
  
ARG JUPYTERHUB_VERSION=1.3.0

RUN adduser --uid 1091 --disabled-password --gecos '' jupyterhub

RUN mkdir -p /srv/jupyterhub

# Required for pycurl
ENV PYCURL_SSL_LIBRARY=openssl
ENV LD_PRELOAD=/lib/libssl.so.1.1
RUN apk update && apk add npm libpq libcurl openssh openssh-client py-cryptography

COPY . /srv/jupyterhub

RUN apk update && \
    apk add --no-cache --virtual .build-dependencies \
                       build-base \
                       cargo \
                       curl-dev \
                       gcc \
                       git \
                       g++ \
                       musl-dev \
                       libffi-dev \
                       libressl-dev \
                       libzmq \
                       openssl-dev \
                       postgresql-dev \
                       python3-dev \
                       py-cryptography \
                       py-pip \
                       rust \
                       swig \
                       zeromq-dev && \
    cd /srv/jupyterhub && pip3 install --upgrade setuptools pip && pip3 install -r dev-requirements.txt && pip3 install -e . && \
    apk del .build-dependencies

ENV LANG=en_US.UTF-8

USER jupyterhub
ENTRYPOINT ["sh", "/srv/jupyterhub/entrypoint.sh"]
