#!/usr/bin/env python3

import base64
import json
import math
import os
import sys
import time
from urllib.request import urlopen

DEV_SECRETS_ROOT = "~/.mcli_dev/"
IDP_URL_FILE = DEV_SECRETS_ROOT + "idp"
USER_INFO_FILE = DEV_SECRETS_ROOT + "user"
PRIVATE_KEY_PATH = DEV_SECRETS_ROOT + "keys/private-key.pem"

ALLOWED_ACTIONS = [
    "REVOKE_AZURE",
    "REVOKE_AWS",
    "PROVISION_AZURE",
    "REVOKE_GCP",
    "PROVISION_AWS",
    "PROVISION_GCP",
    "PROVISION_THIRDPARTY",
]


def help(action, args):
    logger.info("Allowed actions are:")
    for action in ALLOWED_ACTIONS:
        logger.info("-", action)


def execute(action, args):
    """Delegates the execution of the action to the appropriate handler."""

    if action == "PROVISION_AZURE":
        mcli = mcli_as_idp_user()
        ensure_directory_exists(DEV_SECRETS_ROOT + "azure")
        # persist_azure_storage_creds(resp.get('storage_account_name'), resp.get('storage_access_key'))

    elif action == "PROVISION_AWS":
        mcli = mcli_as_idp_user()
        ensure_directory_exists(DEV_SECRETS_ROOT + "aws")

    elif action == "PROVISION_GCP":
        mcli = mcli_as_idp_user()
        ensure_directory_exists(DEV_SECRETS_ROOT + "gcp")

    elif action == "REVOKE_AZURE":
        mcli = mcli_as_idp_user()
        delete_file(DEV_SECRETS_ROOT + "azure/azure.json")
        delete_directory(DEV_SECRETS_ROOT + "azure")
        logger.info("Deleted locally persisted secrets... ")
        logger.info("Successfully revoked provisioned Azure resources...")

    elif action == "REVOKE_AWS":
        mcli = mcli_as_idp_user()
        delete_file(DEV_SECRETS_ROOT + "aws/aws.json")
        delete_directory(DEV_SECRETS_ROOT + "aws")
        logger.info("Deleted locally persisted secrets... ")
        logger.info("Successfully revoked provisioned Aws resources...")

    elif action == "REVOKE_GCP":
        mcli = mcli_as_idp_user()
        delete_file(DEV_SECRETS_ROOT + "gcp/gcp.json")
        delete_directory(DEV_SECRETS_ROOT + "gcp")
        logger.info("Deleted locally persisted secrets... ")
        logger.info("Successfully revoked provisioned Gcp resources...")

    elif action == "PROVISION_THIRDPARTY":
        ensure_directory_exists(DEV_SECRETS_ROOT + "thirdParty")
        mcli = mcli_as_basic_user()

    else:
        help(action, args)


def persist_thirdParty_creds(thirdPartyApiKind, creds):
    filepath = get_absolute_path(DEV_SECRETS_ROOT + "thirdParty/" + thirdPartyApiKind + ".txt")
    with open(filepath, "w") as f:
        f.write(json.dumps(str(creds)))
    logger.info(thirdPartyApiKind + " secrets have been persisted into:", filepath)


def persist_azure_storage_creds(account_name, access_key):
    filepath = get_absolute_path(DEV_SECRETS_ROOT + "azure/azure.json")
    with open(filepath, "w") as f:
        json.dump({"storage_account_name": account_name, "storage_access_key": access_key}, f)
    logger.info("Azure secrets have been persisted into:", filepath)


def persist_aws_storage_creds(access_key, secret_key):
    filepath = get_absolute_path(DEV_SECRETS_ROOT + "aws/aws.json")
    with open(filepath, "w") as f:
        json.dump({"access_key": access_key, "secret_key": secret_key}, f)
    logger.info("Aws secrets have been persisted into:", filepath)


def persist_gcp_storage_creds(account_id, account_email, access_key, secret_key):
    filepath = get_absolute_path(DEV_SECRETS_ROOT + "gcp/gcp.json")
    with open(filepath, "w") as f:
        json.dump(
            {
                "accountId": account_id,
                "accountEmail": account_email,
                "accessKey": access_key,
                "secretKey": secret_key,
            },
            f,
        )
    logger.info("Gcp secrets have been persisted into:", filepath)


def ensure_directory_exists(dirpath):
    dirpath = get_absolute_path(dirpath)
    os.makedirs(dirpath, exist_ok=True)


def delete_directory(dirpath):
    dirpath = get_absolute_path(dirpath)
    if os.path.exists(dirpath):
        os.rmdir(dirpath)


def delete_file(filepath):
    filepath = get_absolute_path(filepath)
    if os.path.exists(filepath):
        os.remove(filepath)


def get_absolute_path(pth):
    pth = os.path.expanduser(pth)
    pth = os.path.abspath(pth)
    return pth


def mcli_as_basic_user():
    url = get_mcli_url()
    token = _create_basic_auth_token("BA", "BA")
    basicAuthHeader = "Basic " + token
    return _fetch_remote_mcli_with_custom_auth(url, basicAuthHeader)


def mcli_as_idp_user():
    url = get_mcli_url()
    user_id = get_user_id()
    token = _create_key_auth_token(user_id, PRIVATE_KEY_PATH)
    keyAuthHeader = "mcli_key " + token
    return _fetch_remote_mcli_with_custom_auth(url, keyAuthHeader)


def get_user_id():
    return _read_line_from_file(USER_INFO_FILE)


def get_mcli_url():
    return _read_line_from_file(IDP_URL_FILE)


def _create_basic_auth_token(user, password):
    basic_content_bytes = "BA:BA".encode("ASCII")
    basic_token_b64 = base64.b64encode(basic_content_bytes).decode("ASCII")
    return basic_token_b64


def _create_key_auth_token(user_id, private_key_path):
    sig, hex_nonce = _generate_signature(private_key_path)
    mcli_key = user_id + ":" + hex_nonce + ":" + sig
    mcli_key_bytes = mcli_key.encode("utf-8")
    mcli_key_b64 = base64.b64encode(mcli_key_bytes).decode("ascii")
    return mcli_key_b64


def _fetch_remote_mcli_with_custom_auth(url, authHeader):
    """Loads and returns the mcli type system."""
    src = urlopen(url + "/remote/mcli.py").read()
    exec_scope = {}
    exec(src, exec_scope)
    return exec_scope["get_mcli"](url=url, authz=authHeader)


def _generate_signature(private_key_path):
    private_key_path = get_absolute_path(private_key_path)
    if not os.path.exists(private_key_path):
        raise Exception("Private key does not exist at path:" + private_key_path)
    nonce = str(math.floor(time.time() * 1000))
    # Generate the signature using the private key
    sig = os.popen(
        "logger.infof "
        + nonce
        + " | openssl dgst -hex -sigopt rsa_padding_mode:pss -sha256 -sign "
        + private_key_path
    ).read()
    # Remove the '(stdin)=' prefix from the output
    sig = sig[len("SHA2-256(stdin)=") :].strip()
    # Encode the nonce in hexadecimal format
    hex_nonce = nonce.encode("ascii").hex()
    return (sig, hex_nonce)


def _read_line_from_file(filepath):
    filepath = get_absolute_path(filepath)
    if not os.path.exists(filepath):
        raise Exception("File does not exist at: " + filepath)
    with open(filepath) as f:
        return f.readline().strip()


def _parse_args(args):
    """Parses the args passed into the python script leaving out the first argument (the script name)."""
    action = args[0]
    return (action, args[1:])


#!/usr/bin/env python3

import json
import os
import sys
from enum import Enum

mcli_DIR = os.getenv("mcli_DIR")
DEV_SECRETS_ROOT = os.path.expanduser("~/.mclidev/")
CLOUD_CREDENTIALS_ROOT_SUBDIR = "server/vault/_/cloud/"
FILE_SYSTEM_CONFIG_SUBDIR = "/server/config/_cluster_/local/FileSystemConfig/"
FILE_SYSTEM_CONFIG_FILE_NAME = "FileSystemConfig.json"


def resetConfig(cloud_name):
    cloud = None
    if cloud_name == CloudName.AWS.value:
        cloud = Cloud(CloudName.AWS.value, "s3", "aws.json", "aws/aws.json")
        cloud.writeCredentials()
    elif cloud_name == CloudName.AZURE.value:
        cloud = Cloud(CloudName.AZURE.value, "adl", "azure.json", "azure/azure.json")
        # TODO PLAT-42946: write azure credentials
    if cloud:
        cloud.writeFileSystemConfig()


def writeJsonToFile(parent_dir, file_path, json_content):
    # create parent directories up to file_path if they do not already exist
    os.makedirs(parent_dir, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(json_content, f)


class CloudName(Enum):
    AWS = "aws"
    AZURE = "azure"


class Cloud:

    def __init__(
        self, name, file_system_name, credentials_file_name, provisioned_credentials_subpath
    ):
        # name of the Cloud
        self.name = name
        # the name of the file system to set mounts to. e.g. 's3'
        self.file_system_name = file_system_name
        # the file name containing CloudCredentials to write into the Config Framework. e.g. 'aws.json'
        self.credentials_file_name = credentials_file_name
        # the subpath to the provisioned credentials file. e.g. '/aws/aws.json'
        self.provisioned_credentials_subpath = provisioned_credentials_subpath

    def writeFileSystemConfig(self):
        logger.info(
            f"Setting {self.file_system_name} as default filesystem at the _cluster_ override"
        )
        file_system_config_dir = mcli_DIR + FILE_SYSTEM_CONFIG_SUBDIR
        file_system_config_path = file_system_config_dir + FILE_SYSTEM_CONFIG_FILE_NAME
        file_system_config_json_map = {}
        file_system_config_json_map["default"] = self.file_system_name
        writeJsonToFile(
            file_system_config_dir, file_system_config_path, file_system_config_json_map
        )

    def writeCredentials(self):
        # write provisioned credentials to the config framework
        provisioned_credentials_path = os.path.join(
            DEV_SECRETS_ROOT, self.provisioned_credentials_subpath
        )
        if not os.path.exists(provisioned_credentials_path):
            logger.info("No provisioned credentials found, please follow documentation")
            return
        with open(provisioned_credentials_path, "r") as provisioned_credentials_file:
            provisioned_credentials_mapping = json.load(provisioned_credentials_file)
            config_credentials_dir = os.path.join(mcli_DIR, CLOUD_CREDENTIALS_ROOT_SUBDIR)
            config_credentials_path = config_credentials_dir + self.credentials_file_name
            logger.info(f"Moving credentials to {config_credentials_path}")
            # CloudCredentials field name -> Cloud dependent values
            credentials_map = {}
            if self.name == CloudName.AWS.value:
                credentials_map["type"] = "AwsCredentials"
                credentials_map["region"] = "us-east-1"
                credentials_map["accessKey"] = provisioned_credentials_mapping["access_key"]
                credentials_map["secretKey"] = provisioned_credentials_mapping["secret_key"]
            elif self.name == CloudName.AZURE.value:
                # TODO: PLAT-42946 need to add remaining Azure fields
                credentials_map["type"] = "AzureCredentials"
                credentials_map["region"] = "eastus2"
                storageCredentials = {}
                storageCredentials["accountName"] = provisioned_credentials_mapping[
                    "storage_account_name"
                ]
                storageCredentials["accessKey"] = provisioned_credentials_mapping[
                    "storage_access_key"
                ]
                credentials_map["storageCredentials"] = storageCredentials

        config_map = {}
        config_map["credentials"] = credentials_map
        writeJsonToFile(config_credentials_dir, config_credentials_path, config_map)


#!/usr/bin/env python3

# Copyright 2009-2022 mcli AI. All Rights Reserved.
# This material, including without limitation any software, is the confidential trade secret and proprietary
# information of mcli and its licensors. Reproduction, use and/or distribution of this material in any form is
# strictly prohibited except as set forth in a written license agreement with mcli and/or its authorized distributors.
# This material may be covered by one or more patents or pending patent applications.

import base64
import builtins
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error

try:
    import kubernetes as k8s

    K8S_CLI_AVAILABLE = True
except ImportError:
    K8S_CLI_AVAILABLE = False


# Configure logger
class FormatWithColors(logging.Formatter):
    COLOR_MAP = {
        logging.DEBUG: "\x1b[34;20m",  # blue
        logging.INFO: "\x1b[38;20m",  # white
        logging.INFO + 1: "\x1b[32;20m",  # green
        logging.WARNING: "\x1b[33;20m",  # yellow
        logging.ERROR: "\x1b[31;20m",  # red
        logging.CRITICAL: "\x1b[31;1m",  # bold red
    }

    def __init__(self, record_format):
        super().__init__()
        self._colors = True
        self._default_formatter = logging.Formatter(record_format)
        self._formatters = {
            level: logging.Formatter(color + record_format + "\x1b[0m")
            for level, color in self.COLOR_MAP.items()
        }

    def no_colors(self, flag):
        self._colors = not flag

    def _formatter(self, level):
        return (
            self._formatters.get(level, self._default_formatter)
            if self._colors
            else self._default_formatter
        )

    def format(self, record):
        return self._formatter(record.levelno).format(record)


logger = logging.getLogger()
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = FormatWithColors("[%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

mcli_SERVER_ROOT = os.getenv("mcli_SERVER_ROOT")
V8_INSTALL_HINT = "Reapplying configuration by running `v8 setup` may fix this issue."


is_macos = platform.system() == "Darwin"
is_linux = platform.system() == "Linux"


def fatal_error(msg):
    logger.critical(msg + " Unable to recover from the error, exiting.")
    if not logger.isEnabledFor(logging.DEBUG):
        logger.error(
            "Debug output may help you to fix this issue or will be useful for maintainers of this tool."
            " Please try to rerun tool with `-d` flag to enable debug output"
        )
    sys.exit(1)


def execute_os_command(command, fail_on_error=True, stdin=None):
    logger.debug("Executing command '%s'", command)
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
    )
    if stdin is not None:
        stdin = stdin.encode()
    stdout, stderr = [stream.decode().strip() for stream in process.communicate(input=stdin)]

    logger.debug("rc    > %s", process.returncode)
    if stdout:
        logger.debug("stdout> %s", stdout)
    if stderr:
        logger.debug("stderr> %s", stderr)

    if process.returncode:
        msg = f'Failed to execute command "{command}", error:\n{stdout}{stderr}'
        if fail_on_error:
            fatal_error(msg)
        else:
            raise RuntimeError(msg)

    return stdout


def service_account_secret_name(context, namespace):
    assert context == "dev", f'Only "dev" context is supported, got "{context}"'
    return f"{namespace}-admin"


def k8s_token(context, namespace, secret_name):
    logger.debug(
        f"Retrieving token from secret {secret_name} in context {context} for namespace {namespace}"
    )
    encoded_token = execute_os_command(
        f"kubectl"
        f" --context {context}"
        f" -n {namespace} get secret {secret_name}"
        f" -o jsonpath='{{.data.token}}'"
    )
    assert (
        encoded_token
    ), f"Failed to retrieve token from secret {secret_name} in context {context} for namespace {namespace}; run `v8 setup` and try again"
    return base64.b64decode(encoded_token).decode()


def k8s_context_name():
    logger.debug("Requesting current k8s context name")
    context = execute_os_command("kubectl config current-context")
    logger.info('Found k8s context  "%s"', context)
    return context


def k8s_api_server_url(context_name):
    logger.debug('Looking for a K8s ApiServer url by context name "%s"', context_name)
    url = execute_os_command(
        f"kubectl config view -o"
        f" jsonpath='{{.clusters[?(@.name==\"{context_name}\")].cluster.server}}'"
    )
    if not url:
        fatal_error(f'Cannot determine K8s APIServer url for context "{context_name}"')
    logger.debug('Current K8s APIServer url for context "%s" is %s', context_name, url)
    return url


def mcli_cluster_url(host):
    # noinspection HttpUrlsUsage
    return f"http://{host}/mcli/mcli"


def configure_K8sApiServer(namespace, context):
    url = k8s_api_server_url(context)
    dsa = service_account_secret_name(context, namespace)
    token = k8s_token(context, namespace, dsa)

    mcli.K8sApiServer().config().clearConfigAndSecretAllOverrides()
    mcli.K8sApiServer.setApiUrlAndAuth(url, f"Bearer {token}", mcli.ConfigOverride.CLUSTER)
    logger.info("mcli K8sApiServer configured!")


def ask_user(prompt):
    return input(f"{prompt} (yes/NO) ").lower() in ["yes", "y", "1", "ye"]


def delete_namespace(context, namespace):
    if namespace == "default":
        logger.debug("Skipping removal for the default namespace")
        return
    logger.info(
        'Deleting namespace "%s" please wait '
        "(It may take some time to ensure all resources are cleaned)",
        namespace,
    )
    try:
        execute_os_command(
            f"kubectl --context={context} delete ns {namespace}", fail_on_error=False
        )
    except BaseException as e:
        if "Error from server (NotFound): namespaces" in str(e):
            return  # no need to report if no namespace found
        logger.warning("Failed to delete namespace. See error:\n%s", str(e))


def configure_k8s_context(namespace, context):
    # This assumes K8s context and minikube profile name are same.

    logger.debug(
        'Configuring mcli Server to use k8s namespace "%s" in context %s', namespace, context
    )
    context_name = k8s_context_name()

    if context_name != context:
        logger.warning(
            f'K8s context configured to different context ("{context_name}") than requested '
            f'context ("{context}").'
        )
        if not ask_user(
            f"Would you like to set context to ({context})"
            f" & namespace to ({namespace}) and proceed forward?"
        ):
            sys.exit(1)
        # noinspection PyBroadException
        try:
            execute_os_command(f"kubectl config use-context {context}")
            logger.info(
                "Configured successfully to Namespace (%s) and Context (%s)", namespace, context
            )
        except BaseException:
            fatal_error(
                f'No context exists with the name: "{context}"'
                f" Run the following command to start minikube:\n"
                f" minikube -p {context} start"
            )


def load_mcli(host):

    if getattr(builtins, "mcli", None) is not None:
        return  # already configured.

    url = f"{mcli_cluster_url(host)}"

    # noinspection PyBroadException
    try:
        from urllib.request import urlopen

        src = urlopen(mcli_cluster_url(host) + "/remote/mcli.py").read()
        exec_scope = {}
        exec(src, exec_scope)  # pylint: disable=exec-used
        builtins.mcli = exec_scope["get_mcli"](url)
    except (urllib.error.HTTPError, urllib.error.URLError, ConnectionRefusedError):
        logger.error(
            f"Cannot connect to mcli server on {url}\nPlease, ensure mcli server is running and try again."
        )
        sys.exit(1)
    except BaseException:
        logger.exception("Failed to load mcli from local server.")
        fatal_error("Please try again.")


def get_next_debug_port():

    def is_port_in_use(port_):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port_)) == 0

    port = 7702
    while is_port_in_use(port):
        port += 1

    return port


def container_access_token(container_registry) -> str:
    """Returns access token for the given container registry"""

    az_login()
    return execute_os_command(
        f"az acr login --name {container_registry} --expose-token --output tsv --query accessToken"
    )


def imagepull_secret_name(container_registry: str) -> str:
    """Returns image pull secret name for the given container registry"""

    return f"{container_registry}-secret"


def ensure_namespace(namespace, context=None):
    context = "" if context is None else f" --context {context}"
    namespaces = json.loads(execute_os_command(f"kubectl{context} get ns -o json")).get("items")
    namespace_exists = any(n.get("metadata").get("name") == namespace for n in namespaces)

    if not namespace_exists:
        logger.debug(f"Creating namespace:${namespace}")
        execute_os_command(f"kubectl{context} create ns {namespace}")


def patch_service_account(
    namespace, container_registry, context=None, service_account_name="default"
):
    """Patches the provided service account with the image pull secret for the given container registry"""

    imagepull_secrets = (
        f'{{"imagePullSecrets": [{{"name": "{imagepull_secret_name(container_registry)}"}}]}}'
    )
    execute_os_command(
        f"kubectl{context} -n {namespace} patch serviceaccount {service_account_name} -p '{imagepull_secrets}' --type=merge"
    )


def configure_registry_secret(namespace, container_registry, context=None):
    ensure_namespace(namespace, context)

    logger.debug(f"Configuring image pull credentials for {container_registry}")

    # https://learn.microsoft.com/en-us/azure/container-registry/container-registry-authentication?tabs=azure-cli#az-acr-login-with---expose-token
    json_credentials = {
        "auths": {
            container_registry: {
                "username": "00000000-0000-0000-0000-000000000000",
                "password": container_access_token(container_registry),
            }
        }
    }

    base64_json_encoded_credentials = base64.b64encode(
        json.dumps(json_credentials).encode("utf-8")
    ).decode()

    context = "" if context is None else f" --context {context}"
    secret = f"""
cat <<EOF | kubectl{context} -n {namespace} apply -f -
apiVersion: v1
data:
  .dockerconfigjson: {base64_json_encoded_credentials}
kind: Secret
metadata:
  name: {imagepull_secret_name(container_registry)}
type: kubernetes.io/dockerconfigjson
EOF"""

    execute_os_command(secret)
    time.sleep(10)
    patch_service_account(namespace, container_registry, context)


def az_login():
    logger.info("Logging into Azure")
    # noinspection PyBroadException
    try:
        execute_os_command("az account show")
    except BaseException:
        fatal_error(
            "Please run `az login` and try again. Run `./v8 setup` if `az` (Azure CLI) is missing"
        )


def uninstall_helm(namespace, release, context):
    logger.info(f"Uninstalling {release} helm chart")
    try:
        execute_os_command(
            "helm uninstall" f" --namespace {namespace}" f" --kube-context {context}" f" {release}",
            fail_on_error=False,
        )
    except BaseException as e:
        logger.warning(f"Failed to uninstall helm chart:\n{str(e)}")


class K8sClient:
    """K8s client for managing resources in a K8s cluster given a context"""

    from contextlib import contextmanager

    def __init__(self, context="dev") -> None:

        if not K8S_CLI_AVAILABLE:
            fatal_error(f"kubernetes package is missing; {V8_INSTALL_HINT}")

        self._context = context
        self._client = k8s.config.new_client_from_config(context=context)

        _, active_context = k8s.config.list_kube_config_contexts()
        self._namespace = active_context["context"]["namespace"]

        assert self._namespace, f"Namespace is not set in K8s context {context}"

    @contextmanager
    def api(self):
        """Context manager for K8s client"""

        with self._client as api:
            try:
                yield api
            except k8s.client.ApiException as e:
                fatal_error("Exception in K8s client: %s\n" % e)

    def delete_resources(self, selector="mcli__cluster-0=0local0"):
        """Delete all resources in the namespace with the provided label selector"""

        #  https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md
        resource_apis = {
            "CoreV1Api": ["service", "config_map", "secret", "pod", "persistent_volume_claim"],
            "AppsV1Api": ["deployment"],
            "NetworkingV1Api": ["ingress", "network_policy"],
        }

        with self.api() as api_client:
            for api, resources in resource_apis.items():
                cli = getattr(k8s.client, api)(api_client)

                for resource in resources:
                    destructor = getattr(cli, f"delete_collection_namespaced_{resource}")
                    destructor(namespace=self._namespace, label_selector=selector)


PKG_JSN_EXT = ".mclipkg.json"
VERSION_FILE_PATH = "platform/platform/src/main/resources/mcli/server/version.txt"

# Paths and subpaths used in exclusion / inclusion
JAVA_PKG_JSN_SUBPATH = "/src/main/mcli/"
PLAT_ZOO_SUBPATH = "platform/zoo" + JAVA_PKG_JSN_SUBPATH
PLAT_ZOO_PKG_JSN_PATH = PLAT_ZOO_SUBPATH + "zoo/zoo" + PKG_JSN_EXT
PLAT_REPO_SERVER_SUBPATH = "platform/repo/server"

# BUILD and TEST RESOURCES (Mostly to exclude when finding pkg json files)
IDE_PKG_JSN_RSRCS = "/out/production/resources/"
GRADLE_PKG_JSN_RSRCS = "/build/resources/main/"
TEST_RSRCS = "/src/test/resources/"

# Keys of Pkg Decl
K_NAME = "name"
K_VERSION = "version"
K_DEPS = "dependencies"
K_COMPAT = "compatibleToVersion"

CSS_LIB = "cssLibrary"


def get_current_version(file_path=VERSION_FILE_PATH):
    """
    Read the version from VERSION_FILE_PATH and return.
    The file is assumed to contain a single word which should be a valid <major>.<minor>.<patch>
    """
    import os

    if not os.path.exists(file_path):
        raise ValueError(f"File '{file_path}' does not exist.")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            version = content.split()[0] if content else None
    except IOError as e:
        logger.info(f"Error reading file {file_path}: {e}")
        return None

    if version == None:
        raise ValueError(f"File '{file_path}' does not contain version.")
    elif is_major_minor_patch(version):
        return version
    else:
        raise ValueError(
            f"File '{file_path}' does not have a valid <major>.<minor>.<patch> version. Version: '{version}'"
        )


def is_major_minor_patch(version):
    """
    Checks if the provided string is a valid <major>.<minor>.<patch>. i.e three integers separated by dots.
    """
    import re

    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, version))


def previous_version(version):
    """
    Assuming that the provided version is a valid <major>.<minor>, return the
    previous version (<major>.<minor>) from it.
    """
    f_version = float(version)
    return str(f_version - 0.1)


def get_pkg_jsn_files(base_dir=".", excludes=[], force_allowed=[]):
    """
    Traverses the directory and collects paths of pkg json files.


    Args:
        base_dir (str): The starting directory for the traversal.
        excludes (list): Exclude all files which contain any of the provided paths / subpaths
        force_allowed (list): Forcefully allow these files in the list even if they get excludes using excludes
    """
    import os

    matched_files = []

    for root, dirs, files in os.walk(base_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if os.path.join(root, d) not in excludes]

        for file in files:
            file_path = os.path.join(root, file)

            # Check for extension and exclusion rules
            if file.endswith(PKG_JSN_EXT):
                if any(e in file_path for e in excludes):
                    # Include the file only if it's in the force_allowed
                    if not any(allowed in file_path for allowed in force_allowed):
                        continue
                matched_files.append(file_path)

    return sorted(matched_files)


def get_platform_pkgs(files):
    """
    Iterate of the file paths and extract the pkg name from it to return a list of pkgs.
    """
    pkgs = []
    # logger.info(files)
    for file_path in files:
        # Include only those files which follows the platform pkg convention
        if any(p in file_path for p in [JAVA_PKG_JSN_SUBPATH, PLAT_REPO_SERVER_SUBPATH]):
            pkgs.append(file_path.split("/")[-1].replace(PKG_JSN_EXT, ""))
    return pkgs


def align_version(
    files,
    platform_pkgs,
    version,
    compatible_to_version,
    ui_pkgs=set(),
    ui_compatible_to_version=None,
    is_platform=False,
):
    """
    Parse all provided mclipkg.json files and update various fields in the package json.
    1. All the platform_pkgs, if they exist in the dependencies, should be updated to the provided version <major>.<minor>
    2. The version field should be changed to the provided version
    3. compatibleToVersion field should be changed to the previous major minor
    4. For near term, ui_pkgs will have their own "compatibleToVersion"
    5. Version and compatibleVersionTo of the Zoo Test pkgs will not be updated.
    """
    import json

    maj_min = version.rsplit(".", 1)[0]
    desired_key_order = ["name", "description", "author", "icon", K_VERSION, K_COMPAT]

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                modified = False

                # update dependencies to major.minor
                if K_DEPS in data and isinstance(data[K_DEPS], dict):
                    for key in platform_pkgs:
                        if key in data[K_DEPS]:
                            val = data[K_DEPS][key]
                            if val == None or val != maj_min:
                                data[K_DEPS][key] = maj_min
                                modified = True

                # If the provided pkg json files are for platform pkgs, only then update version and compatibleToVersion
                if is_platform:
                    # update version to major.minor.patch
                    if (
                        K_VERSION not in data
                        or data[K_VERSION] == None
                        or data[K_VERSION] != version
                    ):
                        data[K_VERSION] = version
                        modified = True

                    # Change the compatibleToVersion based based on the ui pkgs
                    # TODO: PLAT-108921 - Remove special logic for UI pkgs
                    if data[K_NAME] in ui_pkgs:
                        compat_version = ui_compatible_to_version
                    else:
                        compat_version = compatible_to_version

                    # update compatibleToVersion to previous major.minor
                    if (
                        K_COMPAT not in data
                        or data[K_COMPAT] == None
                        or data[K_COMPAT] != compat_version
                    ):
                        data[K_COMPAT] = compat_version
                        modified = True

                if modified:
                    with open(file_path, "w", encoding="utf-8") as file:
                        json.dump(ensure_key_order(data, desired_key_order), file, indent=2)
                    logger.info(f"Updated file: {file_path}")

            except (json.JSONDecodeError, IOError) as e:
                logger.info(f"Error processing file {file_path}: {e}")


def ensure_key_order(json_obj, ordered_keys):
    """
    Ensures that certain keys in the JSON object occur in the specified order.

    Args:
        json_obj (dict): The JSON object to reorder.
        ordered_keys (list): List of keys specifying the desired order.

    Returns:
        OrderedDict: A new JSON object with the specified keys reordered.
    """
    from collections import OrderedDict

    if not isinstance(json_obj, dict):
        raise TypeError("Input must be a JSON object (dictionary).")

    if not isinstance(ordered_keys, list):
        raise TypeError("ordered_keys must be a list of keys.")

    # Create an ordered dictionary
    reordered_json = OrderedDict()

    # Add keys in the specified order if they exist in the JSON object
    for key in ordered_keys:
        if key in json_obj:
            reordered_json[key] = json_obj[key]

    # Add remaining keys in their original order
    for key, value in json_obj.items():
        if key not in reordered_json:
            reordered_json[key] = value

    return reordered_json


def main():
    import argparse

    try:
        version = get_current_version()

        parser = argparse.ArgumentParser(
            description="Script to align the platform pkgDecl versions with version.txt"
        )

        parser.add_argument(
            "--compatibleToVersion",
            type=str,
            help='The compatiableVersionTo for ALL platform pkgs. Default is "platform version" - 1.',
        )
        parser.add_argument(
            "--uiCompatibleToVersion",
            type=str,
            help="The compatiableVersionTo for ALL UI pkgs. Default is the same as --compatibleToVersion. (optional)",
        )

        # Parse arguments
        args = parser.parse_args()

        # Look in root directory (".") and exclude test & build resources and zoo pkgs (but force allow zoo pkg json)
        excludes = [IDE_PKG_JSN_RSRCS, GRADLE_PKG_JSN_RSRCS, TEST_RSRCS, PLAT_ZOO_SUBPATH]
        force_allowed = [PLAT_ZOO_PKG_JSN_PATH]
        pkg_jsn_files = get_pkg_jsn_files(".", excludes, force_allowed)

        # Extract platform pkg names from it
        pkgs = get_platform_pkgs(pkg_jsn_files)
        # TODO - PLAT-108921 - Remove any specialization of ui pkgs in compatibleToVersion
        ui_pkgs = {p for p in pkgs if p.startswith("ui") or p == CSS_LIB}

        # Only look in Zoo but exclude test resources and zoo pkg json
        base_dir = PLAT_ZOO_SUBPATH
        excludes = [PLAT_ZOO_PKG_JSN_PATH, TEST_RSRCS]
        test_pkg_jsn_files = get_pkg_jsn_files(base_dir, excludes)

        compatible_to_version = (
            args.compatibleToVersion
            if args.compatibleToVersion is not None
            else previous_version(version.rsplit(".", 1)[0])
        )
        ui_compatible_to_version = (
            args.uiCompatibleToVersion
            if args.uiCompatibleToVersion is not None
            else compatible_to_version
        )

        # Ensure Version in platform pkgs (align version, compatibleVersionTo and dependencies)
        align_version(
            pkg_jsn_files,
            pkgs,
            version,
            compatible_to_version,
            ui_pkgs,
            ui_compatible_to_version,
            True,
        )
        # Ensure Version in zoo test pkgs (align dependencies only)
        align_version(test_pkg_jsn_files, pkgs, version, None, set(), None, False)
    except ValueError as e:
        logger.info(f"Error: {e}")


if __name__ == "__main__":
    main()
