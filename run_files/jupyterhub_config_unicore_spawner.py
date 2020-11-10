import logging
import os

c = get_config()
c.JupyterHub.log_level = logging.DEBUG
c.JupyterHub.log_format = '%(asctime)s,%(msecs).03d, Levelno=%(levelno)s, Level=%(levelname)s, Logger=%(name)s, File=%(filename)s, Line=%(lineno)d, %(message)s'

c.JupyterHub.default_url = '/hub/home'
c.JupyterHub.jinja_environment_options = {
    "extensions": [
        "jinja2.ext.do",
        "jinja2.ext.loopcontrols",
        "jinja2_ansible_filters.AnsibleCoreFiltersExtension",
    ]
}

from jupyterhub.spawner import BackendSpawner

c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.cancel_progress_activation = 50
c.BackendSpawner.progress_status = [
    {"progress": 20, "message": "Bla1", "html_message": "Bla1",},
    {"progress": 40, "message": "Bla2", "html_message": "Bla2",},
    {"progress": 60, "message": "Bla3", "html_message": "Bla3",},
    {"progress": 80, "message": "Bla4", "html_message": "Bla4",},
]

# c.BackendSpawner.cmd = '/home/kreuzer/work2/source/Jupyter-JSC/jupyterhub/patches/backend_spawner/backend/test_script.sh'
c.JupyterHub.hub_port = 8081
c.JupyterHub.port = 8002
c.ConfigurableHTTPProxy.api_url = 'http://127.0.0.1:8003'

c.JupyterHub.tornado_settings = {'slow_spawn_timeout': 0}


from oauthenticator.generic import GenericOAuthenticator

c.JupyterHub.authenticator_class = GenericOAuthenticator
c.GenericOAuthenticator.extra_authorize_params = dict(
    (x, y)
    for x, y in (
        element.split('=')
        for element in os.environ.get("EXTRA_AUTHORIZE_PARAMS").split(',')
    )
)
c.GenericOAuthenticator.enable_auth_state = True
c.GenericOAuthenticator.client_id = os.environ.get("CLIENT_ID")
c.GenericOAuthenticator.client_secret = os.environ.get("CLIENT_SECRET")
c.GenericOAuthenticator.oauth_callback_url = os.environ.get('CALLBACK_URL')
c.GenericOAuthenticator.authorize_url = os.environ.get('AUTHORIZE_URL')
c.GenericOAuthenticator.token_url = os.environ.get('TOKEN_URL')
c.GenericOAuthenticator.userdata_url = os.environ.get('USERDATA_URL')
c.GenericOAuthenticator.username_key = "username_attr"
c.GenericOAuthenticator.scope = os.environ.get('SCOPE').split(";")
c.GenericOAuthenticator.admin_users = set(os.environ.get('ADMIN_USERS').split(";"))


from tornado.httpclient import HTTPRequest


async def post_auth_hook(authenticator, handler, authentication):
    http_client = authenticator.http_client()
    access_token = authentication["auth_state"]["access_token"]
    url = os.environ.get("TOKENINFO_URL")
    headers = {
        "Accept": "application/json",
        "User-Agent": "JupyterHub",
        "Authorization": f"Bearer {access_token}",
    }
    req = HTTPRequest(url, method="GET", headers=headers,)
    resp = await http_client.fetch(req)
    resp_json = json.loads(resp.body.decode('utf8', 'replace'))
    authentication["auth_state"]["exp"] = resp_json.get('exp')
    return authentication


c.GenericOAuthenticator.post_auth_hook = post_auth_hook

###
# JSC Account Mapping
# Users should only see accounts, systems, partitions, projects and reservations where they have access to
###

import copy
import json
import re

maintenance_path = os.environ.get("MAINTENANCE_PATH")
resources_path = os.environ.get("RESOURCES_PATH")
reservations_path = os.environ.get("RESERVATIONS_PATH")
hdf_cloud_path = os.environ.get("HDF_CLOUD_PATH")


async def options_form(spawner):
    user_auth_state = await spawner.user.get_auth_state()
    user_hpc_accounts = user_auth_state.get('oauth_user', {}).get(
        'hpc_infos_attribute', []
    )
    with open(maintenance_path, "r") as f:
        maintenance_list = json.load(f)
    with open(resources_path, "r") as f:
        resources = json.load(f)
    with open(reservations_path, "r") as f:
        reservations_dict = json.load(f)
    with open(hdf_cloud_path, "r") as f:
        hdf_cloud = json.load(f)

    if 'HDF-Cloud' in maintenance_list:
        hdf_cloud = {}

    def map_partition(system, partition):
        if system == "DEEP":
            if partition == "dam":
                partition = "dp-dam"
            if partition == "booster":
                partition = "dp-esb"
            if partition == "cpu":
                partition = "dp-cn"
        return partition

    s = "^([^\,]+),([^\,\_]+)[_]?([^\,]*),([^\,]*),([^\,]*)$"
    c = re.compile(s)

    def regroup(x):
        groups = list(c.match(x).groups())
        if not groups[2] and groups[1] != "hdfcloud":
            groups[2] = "batch"
        groups[1] = groups[1].upper()
        groups[3] = groups[3].lower()
        groups[2] = map_partition(groups[1], groups[2])
        return groups

    user_hpc_list = [regroup(x) for x in user_hpc_accounts]
    systems = sorted(
        {group[1] for group in user_hpc_list if group[1] not in maintenance_list}
    )

    def add_default_if(groups):
        if groups[2] == "gpus":
            return True
        return False

    def add_default(groups):
        ret = copy.deepcopy(groups)
        if ret[2] == "gpus":
            ret[2] = "develgpus"
        elif ret[2] == "batch":
            ret[2] = "devel"
        return ret

    add_defaults = [add_default(x) for x in user_hpc_list if add_default_if(x)]
    user_hpc_list.extend(add_defaults)

    accounts = {
        system: sorted({group[0] for group in user_hpc_list if system == group[1]})
        for system in systems
    }
    projects = {
        system: {
            account: sorted(
                {
                    group[3]
                    for group in user_hpc_list
                    if system == group[1] and account == group[0]
                }
            )
            for account in accounts[system]
        }
        for system in systems
    }

    partitions = {
        system: {
            account: {
                project: sorted(
                    {
                        group[2]
                        for group in user_hpc_list
                        if system == group[1]
                        and account == group[0]
                        and project == group[3]
                        and group[2] in resources.get(system, {}).keys()
                    }
                )
                for project in projects[system][account]
            }
            for account in accounts[system]
        }
        for system in systems
    }
    reservations_list = {
        system: list(x.split(';') for x in reservations_dict.get(system, []))
        for system in reservations_dict.keys()
    }
    reservations = {
        system: {
            account: {
                project: {
                    partition: sorted(
                        [
                            x[0]
                            for x in reservations_list.get(system, [])
                            if (
                                (
                                    project in x[12].split(',')
                                    or account in x[11].split(",")
                                )
                                and ((not x[8]) or partition in x[8].split(","))
                            )
                        ]
                    )
                    for partition in partitions[system][account][project]
                }
                for project in projects[system][account]
            }
            for account in accounts[system]
        }
        for system in systems
    }
    dropdown_lists = {
        "systems": systems,
        "accounts": accounts,
        "projects": projects,
        "partitions": partitions,
        "reservations": reservations,
    }

    def replace_resource(key, resource):
        value = resource[key]
        if type(value) is int or type(value) is list:
            return value
        else:
            return value.replace("_min_", str(resource["MINMAX"][0])).replace(
                "_max_", str(resource["MINMAX"][1])
            )

    resources_replaced = {
        system: {
            partition: {
                resource: {
                    key: replace_resource(key, resources[system][partition][resource])
                    for key in resources[system][partition][resource].keys()
                }
                for resource in resources[system][partition].keys()
            }
            for partition in resources[system].keys()
        }
        for system in resources.keys()
    }
    return {
        "dropdown_lists": dropdown_lists,
        "reservations": reservations_list,
        "resources": resources_replaced,
        "hdfcloud": hdf_cloud.keys(),
        "maintenance": maintenance_list,
    }


async def options_from_form(spawner, formdata):
    with open(resources_path, "r") as f:
        resources = json.load(f)
    resourcemapping = {"nodes": "Nodes", "runtime": "Runtime", "gpus": "GPUS"}

    def skip_resources(key, value):
        if key.startswith("resource_"):
            if formdata.get('system_input')[0] == 'hdfcloud':
                return False
            elif formdata.get('partition_input')[0] == 'LoginNode':
                return False
            else:
                resource_name = key[len("resource_") : -len("_name")]
                if (
                    resourcemapping.get(resource_name, resource_name)
                    not in resources.get(formdata.get('system_input')[0].upper())
                    .get(formdata.get('partition_input')[0])
                    .keys()
                ):
                    return False
        else:
            if value in ["undefined", "None"]:
                return False
        return True

    ret = {
        key: value[0]
        for key, value in formdata.items()
        if skip_resources(key, value[0])
    }
    return ret


c.BackendSpawner.options_from_form = options_from_form
c.BackendSpawner.options_form = options_form
