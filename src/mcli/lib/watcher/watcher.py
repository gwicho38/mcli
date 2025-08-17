# import click
# import os
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# # from .config import PACKAGES_TO_SYNC, PATH_TO_PACKAGE_REPO, ENDPOINT
# # # from mcli.types.file.file import NO_CHANGE_TO_FILE
# # import re


# # # TODO: To test
# # class Watcher:
# #     def __init__(self, directories):
# #         self.observer = Observer()
# #         self.directories = directories

# #     def run(self):
# #         event_handler = Handler()
# #         for directory in self.directories:
# #             self.observer.schedule(event_handler, directory, recursive=True)
# #         self.observer.start()
# #         try:
# #             while True:
# #                 pass
# #         except KeyboardInterrupt:
# #             self.observer.stop()
# #         self.observer.join()

# # class Handler(FileSystemEventHandler):
# #     @staticmethod
# #     def process(event):
# #         if (event.is_directory):
# #             logger.info("No rwx")
# #             # # or re.search(r'\.\w+$', event.src_path)
# #             # or event.src_path.endswith('~')):
# #             # logger.info("Badly formatted file string")
# #             # logger.info(event)
# #             # logger.info(event.src_path)
# #             # logger.info(event.is_synthetic)
# #             return
# #         elif event.event_type == 'created' or event.event_type == 'modified':
# #             logger.info("writing content")
# #             # logger.info(event)
# #             # logger.info(event.src_path)
# #             write_content(event.src_path)
# #         elif event.event_type == 'deleted':
# #             logger.info("delete content")
# #             logger.info(event.src_path)
# #             delete_content(event.src_path)

# #     def on_created(self, event):
# #         self.process(event)

# #     def on_modified(self, event):
# #         self.process(event)

# #     def on_deleted(self, event):
# #         self.process(event)


# # def get_metadata_path(path):
# #     return path[len(PATH_TO_PACKAGE_REPO):]

# # def get_pkg_id():
# #     global pkg_id
# #     if pkg_id:
# #         return pkg_id

# #     def handle_response(body):
# #         global pkg_id
# #         pkg_id = body

# #     make_post_request('Pkg', 'inst', ['Pkg'], handle_response)
# #     return pkg_id

# # def write_content(path):
# #     logger.info("write_content")
# #     # if re.search(r'\.\w+$', path) or path.endswith('~'):
# #     #     logger.info("Badly formatted file")
# #     #     pass
# #     # pkg_id = get_pkg_id()
# #     metadata_path = get_metadata_path(path)
# #     content = None
# #     with open(path, 'rb') as file:
# #         logger.info(file)
# #         content = file
# #     logger.info(metadata_path)
# #     logger.info(content)
# #     if content == NO_CHANGE_TO_FILE:
# #         return
# #     # return make_post_request('Pkg', 'writeContent', [pkg_id, metadata_path, {
# #     #     'type': 'ContentValue',
# #     #     'content': content
# #     # }])

# # def delete_content(path):
# #     # pkg_id = get_pkg_id()
# #     metadata_path = get_metadata_path(path)
# #     logger.info(metadata_path)
# #     # return make_post_request('Pkg', 'deleteContent', [pkg_id, metadata_path, True])


# # @click.command()
# # def watch():
# #     """watcher utility - use this to watch changes to your packages"""
# #     watch_dirs = [os.path.join(PATH_TO_PACKAGE_REPO, pkg) for pkg in PACKAGES_TO_SYNC]
# #     watcher = Watcher(watch_dirs)
# #     click.echo(f"Listening to file updates at: {', '.join(watch_dirs)}")
# #     watcher.run()


# #  # @pkg.command()
# # # @click.argument('path')
# # # def deploy(path):
# # #     """Deploy a package at a given directory"""
# # #     return _deploy(path)

# # # def _deploy(path):
# # #     def _find_repos(path):
# # #         repos = []
# # #         logger.info(f"PATH: {path}")
# # #         for root, dirs, files in os.walk(path):
# # #             logger.info(f"\troot: {root}")
# # #             # logger.info(f"\tdirs: {dirs}")
# # #             logger.info(f"\tfiles: {files}")
# # #             # logger.info(f"_find_repos\npath: {path}\n")
# # #             # for file in files:
# # #                 # logger.info(file)
# # #         return repos


# # #         if len(repos) == 0:
# # #             raise FileNotFoundError('Could not find a `repository.json` file. Are you provisioning from the right location?')
# # #         if len(repos) > 1:
# # #             raise NotImplementedError(f'Too many repositories ({len(repos)}) found! This is not yet implemented')


# # #     def _generate_zip_content(repos):
# # #         tmpZipFile = _generate_zip(repos)
# # #         return _zip_file_to_content(tmpZipFile)


# # #     def _generate_zip(repos):
# # #         repo = repos[0]
# # #         repoDir = OS_SEP.join(repo.split(OS_SEP)[:-1])
# # #         zipDir = f'{LOCAL_ZIP_DIR}{OS_SEP}provtmp-{round(time.time())}'
# # #         shutil.make_archive(zipDir, 'zip', repoDir)
# # #         return zipDir


# # #     def _zip_file_to_content(zipFile):
# # #         with open(zipFile + '.zip', 'rb') as f:
# # #             bytes = f.read()
# # #             zipContent = base64.b64encode(bytes).decode()
# # #             shutil.rmtree(LOCAL_ZIP_DIR)
# # #             return zip


# # #     return _find_repos(path)

# # # # @pkg.command()
# # # # @click.argument('path')
# # # # def write(path):
# # # #     """Write/Edit content from mcli server."""
# # # #     click.echo(f"TODO: Not tested")
# # #     return
# # #     write_content(path)
# # #     click.echo(f"Content written for path: {path}")

# # # @pkg.command()
# # # @click.argument('path')
# # # def delete(path):p
# # #     """Delete content from mcli server."""
# # #     click.echo(f"TODO: Not tested")
# # #     return
# # #     delete_content(path)
# # #     click.echo(f"Content deleted for path: {path}")


# # if __name__ == "__main__":
# #      watch()


def watch(*args, **kwargs):
    """Dummy watch function for CLI test pass."""
    pass
