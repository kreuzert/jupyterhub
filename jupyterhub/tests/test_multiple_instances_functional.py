import json
import os
import requests

import pytest
import tempfile

from contextlib import closing
from subprocess import Popen
from urllib.parse import urlparse
from urllib.parse import unquote
from traitlets.config import Config


from ..utils import url_path_join as ujoin
from ..utils import wait_for_http_server
from .mocking import MockHub
from .test_api import add_user
from .test_api import api_request


def get_proxy_routes(proxy_api_url, auth_token, waitfor):
    waitfor = unquote(waitfor)
    if waitfor.endswith('/'):
        waitfor2 = waitfor[:-1]
    else:
        waitfor2 = waitfor
    routes = {}
    TIMEOUT = 10
    import time
    tac = tic = time.time()
    while tac < tic + TIMEOUT:        
        with closing(
            requests.get(
                f"{proxy_api_url}/api/routes",
                headers={ "Authorization": f"token {auth_token}" }
                )
            ) as r:
            assert r.status_code == 200
            try:
                routes = json.loads(r.text)
            except:
                print("Could not build dict: {}".format(r.text))
                assert False
            if waitfor in routes or waitfor2 in routes:
                print("Return Proxy routes: {}".format(routes))
                return routes
            time.sleep(0.4)
            tac = time.time()
    assert waitfor in routes or waitfor2 in routes

def start_external_jupyterhub(auth_token, base_url, port, proxy_ip, proxy_api_port, td):
    conf_string = (
        "c = get_config()\n"
        "c.JupyterHub.log_level = 10\n"
        "#c.JupyterHub.base_url = '/1'\n"
        "c.JupyterHub.bind_url = 'http://:{port}{base_url}'\n"
        "c.JupyterHub.hub_bind_url = 'http://:{port}{base_url}'\n"
        "#c.JupyterHub.hub_port = 8061\n"
        "c.JupyterHub.tornado_settings = {{ 'version_hash': '' }}\n"

        "c.ConfigurableHTTPProxy.should_start = False\n"
        "c.ConfigurableHTTPProxy.auth_token = \"{auth_token}\"\n"
        "c.ConfigurableHTTPProxy.api_url = \"http://{proxy_ip}:{proxy_api_port}\"\n"
        "".format(port=port,
                  base_url=base_url,
                  auth_token=auth_token,
                  proxy_ip=proxy_ip,
                  proxy_api_port=proxy_api_port)
    )
    with open ('{}/jupyterhub_config.py'.format(td), 'w') as f:
        f.write(conf_string)
    env = os.environ.copy()
    cmd = [
        'jupyterhub',
        '-f',
        '{}/jupyterhub_config.py'.format(td)
    ]
    hub = Popen(cmd, env=env)
    return hub

def start_external_proxy(auth_token, ip, port, api_ip, api_port):
    env = os.environ.copy()
    env["CONFIGPROXY_AUTH_TOKEN"] = auth_token
    cmd = [
        'configurable-http-proxy',
        '--ip',
        ip,
        '--port',
        str(port),
        '--api-ip',
        api_ip,
        '--api-port',
        str(api_port),
        '--log-level=debug',
    ]
    proxy = Popen(cmd, env=env)
    return proxy

async def create_app_without_proxy(request, auth_token, app_base_url, app_port, proxy_ip, proxy_port, proxy_api_port):
    cfg = Config()
    
    cfg.JupyterHub.base_url = f'{app_base_url}'
    cfg.JupyterHub.bind_url = f'http://:{app_port}'
    cfg.JupyterHub.hub_port = app_port
    cfg.JupyterHub.tornado_settings = { "version_hash": "" }
    cfg.ConfigurableHTTPProxy.auth_token = auth_token
    cfg.ConfigurableHTTPProxy.api_url = 'http://%s:%i' % (proxy_ip, proxy_api_port)
    cfg.ConfigurableHTTPProxy.should_start = False

    app = MockHub.instance(config=cfg)
    # disable last_activity polling to avoid check_routes being called during the test,
    # which races with some of our test conditions
    app.last_activity_interval = 0

    def fin():
        MockHub.clear_instance()
        app.http_server.stop()

    request.addfinalizer(fin)

    def wait_for_proxy():
        return wait_for_http_server('http://%s:%i' % (proxy_ip, proxy_port))

    await wait_for_proxy()

    await app.initialize([])
    await app.start()
    return app


async def test_external_jupyterhubs_do_not_delete_routes_of_eachother(request):
    td = tempfile.TemporaryDirectory()
    def del_td():
        td.cleanup()
    request.addfinalizer(del_td)

    auth_token = 'secret!'
    proxy_ip = '127.0.0.1'
    proxy_port = 54320
    proxy_api_ip = '127.0.0.1'
    proxy_api_port = 54321

    # Start external proxy
    proxy = start_external_proxy(auth_token, proxy_ip, proxy_port, proxy_api_ip, proxy_api_port)
    def _cleanup_proxy():
        if proxy.poll() is None:
            proxy.terminate()
            proxy.wait(timeout=10)

    request.addfinalizer(_cleanup_proxy)

    def wait_for_proxy():
        return wait_for_http_server('http://%s:%i' % (proxy_ip, proxy_port))

    await wait_for_proxy()


    # Start external JupyterHub
    hub_port = 54331
    hub_base_url = '/1'
    
    hub = start_external_jupyterhub(auth_token, hub_base_url, hub_port, proxy_ip, proxy_api_port, td.name)
    def term_hub():
        hub.terminate()
    request.addfinalizer(term_hub)

    proxy_api_url = f"http://{proxy_api_ip}:{proxy_api_port}"
    routes = get_proxy_routes(proxy_api_url, auth_token, hub_base_url)
    assert hub_base_url in routes
    

    # Start second external JupyterHub
    hub_port_2 = 54332
    hub_base_url_2 = '/2'
    
    hub_2 = start_external_jupyterhub(auth_token, hub_base_url_2, hub_port_2, proxy_ip, proxy_api_port, td.name)
    def term_hub_2():
        hub_2.terminate()
    request.addfinalizer(term_hub_2)

    proxy_api_url = f"http://{proxy_api_ip}:{proxy_api_port}"
    routes = get_proxy_routes(proxy_api_url, auth_token, hub_base_url_2)
    assert hub_base_url_2 in routes
    print(routes)
    assert hub_base_url in routes and hub_base_url_2 in routes