from requests import Request, Session
from mcli.lib.config.config import ENDPOINT
from mcli.lib.files.files import NO_CHANGE_TO_FILE
from mcli.lib.shell.shell import shell_exec, get_shell_script_path
import re
from mcli.lib.logger.logger import get_logger
logger = get_logger(__name__)
PATH_TO_PACKAGE_REPO = ""

pkg_id = None
s = Session()

# TODO: Not tested nor implemented

class MCLIHeader:
    def __init__(self, 
                 auth: str = None, 
                 mime_type: str = None, 
                 tenant: str = None,
                 tag: str = None,
                 content_type: str = None):
        self.auth = auth
        self.mime_type = mime_type
        self.tenant = tenant
        self.tag = tag
        self.content_type = content_type

    def __str__(self):
        return (f"Headers: AUTH: {self.auth}, MIME_TYPE: {self.mime_type}, TENANT: {self.tenant}, TAG: {self.tag}, CONTENT_TYPE: {self.content_type}")
    
    
class MCLIRequest:
    def __init__(self, 
                 url: str, 
                 mcli_type: str, 
                 mcli_method: str, 
                 method: str,
                 data: any):
        self.mcli_type = mcli_type
        self.mcli_method = mcli_method
        self.method = method
        self.url = url
        self.data = data

    def __str__(self):
        return (f"{self.method}MCLI_URL_MCLI{self.url}MCLI_TYPE_MCLI{self.mcli_type}MCLI_METHOD_MCLI{self.mcli_method}MCLI_DATA_MCLI{self.data}")


def format_prepped_request(prepped, encoding=None):
    # prepped has .method, .path_url, .headers and .body attribute to view the request
    encoding = encoding or requests.utils.get_encoding_from_headers(prepped.headers)
    body = prepped.body.decode(encoding) if encoding else "<binary data>"
    headers = "\n".join(["{}: {}".format(*hv) for hv in prepped.headers.items()])
    return


# TODO: Not tested


def make_post_request(type_name, method, data, on_success=None):
    logger.info("make_post_request")
    logger.info(f"{type_name}, {method}, {data}")
    url = f""
    headers = {"Authorization": AUTH_TOKEN, "Content-Type": "application/json"}
    req = Request(method="GET", url=url, headers=headers, data=data)
    # prepped = s.prepare_request(req)
    logger.info(str(req))
    return


def get_metadata_path(path):
    return path[len(PATH_TO_PACKAGE_REPO) :]


def get_pkg_id():
    global pkg_id
    if pkg_id:
        return pkg_id

    def handle_response(body):
        global pkg_id
        pkg_id = body

    make_post_request("Pkg", "inst", ["Pkg"], handle_response)
    return pkg_id


# TODO: Not tested


def write_content(path):
    logger.info("write_content")
    if re.search(r"\.\w+$", path) or path.endswith("~"):
        logger.info("Badly formatted file")
        pass
    pkg_id = get_pkg_id()
    metadata_path = get_metadata_path(path)
    content = None
    with open(path, "rb") as file:
        logger.info(file)
        content = file
    logger.info(metadata_path)
    logger.info(content)
    if content == NO_CHANGE_TO_FILE:
        return{}


def delete_content(path: str):
    pkg_id = get_pkg_id()
    metadata_path = get_metadata_path(path)
    return make_post_request("Pkg", "deleteContent", [pkg_id, metadata_path, True])


def mcli_request(shell_command: str,
               mcli_request: MCLIRequest, 
               mcli_header: MCLIHeader, 
               on_success = None) -> None:
    path = get_shell_script_path("api", __file__)
    shell_exec(path, 'request', mcli_request, mcli_header)


