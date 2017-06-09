"""Connect Authenticate and get node objects from AWS, Azure and GCP.

License:

    MCC - Unified CLI Utility for AWS, Azure and GCP Instance Control.
    Copyright (C) 2017  Robert Peteuil

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

URL:       https://github.com/robertpeteuil/multi-cloud-control
Author:    Robert Peteuil

"""
from __future__ import absolute_import, print_function
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from mcc.confdir import CONFIG_DIR
from multiprocessing import cpu_count
import sys
import os
import gevent
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()


def begin_collect(cred, providers):
    """Check the host machine and determine collection function to use."""
    if os.uname()[4].startswith("arm"):
        collfunc = collect_data
    elif cpu_count() == 1:
        collfunc = collect_data
    else:
        collfunc = collect_data_mt
    node_list = collfunc(cred, providers)
    conn_objs = {}
    return (node_list, conn_objs)


def collect_data(cred, providers):
    """Orchestrate collection of node data from all providers with a pool."""
    cld_svc_map = {"aws": get_aws,
                   "azure": get_az,
                   "gcp": get_gcp}
    collec_fn = []
    for item in providers:
        collec_fn.append([cld_svc_map[item], cred])
    node_list = []
    node_list = map(get_conn_new, collec_fn)
    return node_list


def collect_data_mt(cred, providers):
    """Orchestrate collection of node data with gevent lib."""
    cld_svc_map = {"aws": get_aws,
                   "azure": get_az,
                   "gcp": get_gcp}
    # turn on display-indicator to indicated working
    busy_obj = busy_disp_on()
    collec_fn = []
    for item in providers:
        collec_fn.append([cld_svc_map[item], cred])
    # fetch nodes
    node_list = []
    pool = Pool()
    node_list = pool.map(get_conn_new, collec_fn)
    pool.join()
    # turn off display-indicator that indicated working
    busy_disp_off(dobj=busy_obj)
    return node_list


def get_conn_new(flist):
    """Call function and make connection."""
    cnodes = []
    cnodes = flist[0](flist[1])
    return cnodes


def busy_disp_on():
    """Turn ON busy_display to show working statues."""
    p = gevent.spawn(busy_display)
    return p


def busy_disp_off(dobj):
    """Turn OFF busy_display to show working statues."""
    dobj.kill(block=False)
    sys.stdout.write("\033[A\n")
    sys.stdout.write("                                                 \r")
    sys.stdout.write("\033[?25h")  # turn cusor back on
    sys.stdout.flush()


def busy_display():
    """Display animation while loading."""
    from time import sleep
    sys.stdout.write("\033[?25l")  # turn cursor off
    sys.stdout.flush()
    for x in range(200):
        symb = ['\\', '|', '/', '-']
        sys.stdout.write('\rAuthentication & Node Retrieval: %s'
                         % (symb[x % 4]))
        sys.stdout.flush()
        sleep(0.12)


def ip_to_str(raw_ip):
    """Convert IP Address list to string or null."""
    if raw_ip:
        raw_ip = raw_ip[0]
    else:
        raw_ip = None
    return raw_ip


def get_aws(cred):
    """Establish connection to AWS service."""
    driver = get_driver(Provider.EC2)
    aws_obj = driver(cred['aws_access_key_id'],
                     cred['aws_secret_access_key'],
                     region=cred['aws_default_region'])
    aws_nodes = []
    aws_nodes = aws_obj.list_nodes()
    aws_nodes = clean_aws(aws_nodes)
    return aws_nodes


def clean_aws(aws_nodes):
    """Retreive details specific to AWS."""
    for node in aws_nodes:
        node.cloud = "aws"
        node.private_ips = ip_to_str(node.private_ips)
        node.public_ips = ip_to_str(node.public_ips)
        node.zone = node.extra['availability']
        node.size = node.extra['instance_type']
        node.type = node.extra['instance_lifecycle']
    return aws_nodes


def get_az(cred):
    """Establish connection to Azure service."""
    driver = get_driver(Provider.AZURE_ARM)
    az_obj = driver(tenant_id=cred['az_tenant_id'],
                    subscription_id=cred['az_sub_id'],
                    key=cred['az_app_id'],
                    secret=cred['az_app_sec'])
    az_nodes = []
    az_nodes = az_obj.list_nodes()
    az_nodes = clean_az(az_nodes)
    return az_nodes


def clean_az(az_nodes):
    """Retreive details specific to Azure."""
    for node in az_nodes:
        node.cloud = "azure"
        node.private_ips = ip_to_str(node.private_ips)
        node.public_ips = ip_to_str(node.public_ips)
        node.zone = node.extra['location']
        node.size = node.extra['properties']['hardwareProfile']['vmSize']
        group_raw = node.id
        unnsc, group_end = group_raw.split("resourceGroups/", 1)
        group, unnsc = group_end.split("/", 1)
        node.group = group
    return az_nodes


def get_gcp(cred):
    """Establish connection to GCP."""
    driver = get_driver(Provider.GCE)
    gcp_pem = CONFIG_DIR + cred['gcp_pem_file']
    gcp_obj = driver(cred['gcp_svc_acct_email'],
                     gcp_pem,
                     project=cred['gcp_proj_id'])
    gcp_nodes = []
    gcp_nodes = gcp_obj.list_nodes(ex_use_disk_cache=True)
    gcp_nodes = clean_gcp(gcp_nodes)
    return gcp_nodes


def clean_gcp(gcp_nodes):
    """Retreive details specific to GCP."""
    for node in gcp_nodes:
        node.cloud = "gcp"
        node.private_ips = ip_to_str(node.private_ips)
        node.public_ips = ip_to_str(node.public_ips)
        node.zone = node.extra['zone'].name
    return gcp_nodes
