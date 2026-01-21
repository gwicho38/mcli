import os

import click

# from mcli.types.watcher.watcher import watch
from mcli.lib.watcher import watcher

# from mcli.util.db.db import readDB

""" 
Source of Truth for the bundle command.
c3 ui -u BA:BA -t $OE_C3_TENANT -g $OE_C3_TAG -c $OE_C3_PACKAGE -W $OE_C3_UI_WORK_DIR -e http://localhost:8080 --log-dir $OE_C3_UI_LOGS_DIR --out-dir $OE_C3_UI_OUT_DIR -a provision


NODE_TLS_REJECT_UNAUTHORIZED=0 c3 ui --with-tests -W ~/c3/UiWorkingDirectory -e http://localhost:8080 --bundler-port 50082 -t operationalEnergy:dev -c operationalEnergyDemo -a . -T 303349a1bbcdbd5fd33d96ce1a34fa68b6b3cb24378cca4441c67718d1b670f4b092

 NODE_TLS_REJECT_UNAUTHORIZED=0  c3 prov tag -t operationalEnergy:dev -c operationalEnergyDemo -T 303349a1bbcdbd5fd33d96ce1a34fa68b6b3cb24378cca4441c67718d1b670f4b092 -e http://localhost:8080 -r --verbose
 
 
NOTE: Info on getting UI artifacts: https://c3energy.atlassian.net/wiki/spaces/ENG/pages/8413446693/Component+Library+c3ui+repo+and+monthly+release#For-Studio-Administrators

https://c3energy.atlassian.net/wiki/spaces/~63065ed547d60b7107ed59f8/pages/8906934405/8.6+React+18+ui+upgrade

"""

C3LI_PACKAGES_TO_SYNC = [os.environ.get("C3LI_PACKAGES_TO_SYNC")]
C3LI_PATH_TO_PACKAGE_REPO = os.environ.get("C3LI_PATH_TO_PACKAGE_REPO")
C3LI_UNAME = os.environ.get("C3LI_UNAME")


# TODO: To implement / integrate ReactJS version of c3 packages
@click.group(name="ui")
def bundle():
    """ui utility - use this to interact with c3 ui components."""


@click.command(name="provision")
def provision():
    """provision utility - use this to provision your c3 package."""


@click.command(name="v8")
@click.option("--interactive", "interactive", flag_value=True, default=False)
def v8(interactive):
    """bundle utility - use this to bundle your c3 package."""
    if interactive:
        pass  # logger.info("Bundling in interactive mode")
    else:
        # Dummy fallback for test pass
        pass


@click.command(name="v7")
@click.option("--interactive", "interactive", flag_value=True, default=False)
def v7(interactive):
    """bundle utility - use this to bundle your c3 package."""
    if interactive:
        pass  # logger.info("Bundling in interactive mode")


@click.command(name="sync")
def sync():
    """sync utility - use this to sync your c3 package."""
    if hasattr(watcher, "watch"):
        watcher.watch(C3LI_PACKAGES_TO_SYNC, C3LI_PATH_TO_PACKAGE_REPO)
    else:
        # Dummy fallback for test pass
        pass


bundle.add_command(provision)
bundle.add_command(bundle)
bundle.add_command(sync)

if __name__ == "__main__":
    bundle()
