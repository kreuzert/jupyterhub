
from contextlib import closing

import requests

from urllib.parse import quote

from ..utils import url_path_join as ujoin

from .test_api import add_user
from .test_api import api_request
from .test_proxy import disable_check_routes
from .test_multiple_instances_functional import get_proxy_routes


async def test_check_routes_dont_delete_hubs(app, disable_check_routes):
    assert app.multiple_instances 
    other_base_url = "/@/some differenturl"
    other_host = "http://127.0.0.1:8071"
    assert other_base_url != app.base_url
    assert other_host != app.hub.host
    proxy = app.proxy
    auth_token = proxy.auth_token
    get_proxy_routes(proxy.api_url, auth_token, app.hub.routespec)


    # simulate other jupyterhub which adds its initial route
    url = ujoin(
        proxy.api_url,
        "api",
        "routes",
        quote(other_base_url)
    )
    headers = {
        "Authorization": "token {auth_token}".format(auth_token=auth_token)
    }
    data = {
        "hub": "True",
        "target": "{other_host}".format(other_host=other_host),
        "jupyterhub": "True"
    }
    print(data)
    
    with closing(
        requests.post(
            url,
            headers = headers,
            json = data
        )
    ) as r:
        assert r.status_code == 201
    
    # check that all routes are there
    get_proxy_routes(proxy.api_url, auth_token, other_base_url)

    # now we call check_routes. This will normally delete other_host in routes
    await app.proxy.check_routes(app.users, app._service_map)

    get_proxy_routes(proxy.api_url, auth_token, other_base_url)
    assert False