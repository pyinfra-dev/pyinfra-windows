"""
Manage ``winget`` packages (https://learn.microsoft.com/en-us/windows/package-manager/).
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.operations.util.packaging import PkgInfo, ensure_packages

from pyinfra_windows.facts.winget import WingetPackages


def _package_format_fn(name: str, operator: str, version: str):
    return "winget install --no-upgrade --silent --exact {name} {operator} {version};".format(
        name=name, operator=operator, version=version
    )


@operation()
def packages(packages: str | list[str] | None = None, present=True, latest=False):
    """
    Add/remove/update ``winget`` packages.

    + packages: list of packages to ensure. Must be specified via package ids.
    + present: whether the packages should be installed

    Versions:
        Package versions can be pinned like apt: ``<pkg>=<version>``.

    **Example:**

    .. code:: python

        # Note: Assumes that 'winget' is installed and
        #       user has Administrator permission.
        winget.packages(
            name="Install Notepad++",
            packages=["Notepad++.Notepad++"],
        )
    """
    # TODO when an older version of
    # exists and a newer verision is requested
    # winget still runs but raises and error

    if not packages:
        return

    if isinstance(packages, str):
        packages = [packages]

    packages: list[str] = packages

    requested_packages: list[PkgInfo] = []
    for p in packages:
        if present:
            # this is a hack to support winget istall package --version version
            # each package must have it's own winget install command
            p = p.replace("=", "--version")
            package_info = PkgInfo.from_possible_pair(p, "--version")
            pkg_info_wrapper = PkgInfo(
                name=package_info.name,
                operator=package_info.operator,
                version=package_info.version,
                url="",
                inst_vers_format_fn=_package_format_fn,
            )
            requested_packages.append(pkg_info_wrapper)
        else:
            raise RuntimeError(
                "Uninstalling winget packages is not currently supported."
            )

    # uninstall_command = (
    #    "winget uninstall --silent --exact --id {package_id}{version_cmd};"
    # )

    yield from ensure_packages(
        host,
        requested_packages,
        host.get_fact(WingetPackages),
        present,
        install_command="",
        uninstall_command="",
    )
