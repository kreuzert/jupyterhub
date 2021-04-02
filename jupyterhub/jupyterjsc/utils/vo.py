import json
import os


def get_vos(auth_state, username, admin=False, vo_active=None):
    # Update available VOs for users
    used_authenticator = auth_state.get("oauth_user", {}).get(
        "used_authenticator_attr", "unknown"
    )
    vo_config_file = os.environ.get("VO_CONFIG_PATH")
    with open(vo_config_file, 'r') as f:
        vo_config = json.load(f)
    vo_available_with_weight = []
    for vo_name, vo_infos in vo_config.get("values", {}).items():
        if (
            used_authenticator in vo_infos.get("authenticators", [])
            or username in vo_infos.get("usernames", [])
            or (admin and vo_infos.get("admin", False))
        ):
            vo_available_with_weight.append((vo_name, vo_infos.get("weight", 99)))
    vo_available_with_weight.sort(key=lambda x: x[1])
    vo_available = []
    for x in vo_available_with_weight:
        vo_available.append(x[0])
        if vo_config.get("values", {}).get(x[0], {}).get("exclusive", False):
            vo_available = [x[0]]
            break
    if not vo_active or vo_active not in vo_available:
        vo_active = vo_available[0]
    return vo_active, vo_available
