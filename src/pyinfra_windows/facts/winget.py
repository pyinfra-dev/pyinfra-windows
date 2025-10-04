from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from pyinfra.facts.util.packaging import parse_packages

WINGET_REGEX = r"([^\s]+)\s+([^\s]+)"


class WingetPackages(FactBase):
    """Returns a dict of installed winget packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "Get-WingetPackage | Select -Property Id, InstalledVersion"

    shell_executable = "ps"

    default = dict

    @override
    def process(self, output):
        return parse_packages(WINGET_REGEX, output)
