"""
.. warning::
    This connector is in alpha and may change in future releases.

Some Windows facts and Windows operations work but this is to be considered
experimental. For now, only ``username`` and ``password`` is
being used. There are other methods for authentication, but they have not yet
been added/experimented with.

The ``@winrm`` connector can be used to communicate with Windows instances that have WinRM enabled.

Examples using ``@winrm``:

.. code:: python

    # Get the windows_home fact
    pyinfra @winrm/192.168.3.232 --user vagrant \\
        --password vagrant --port 5985 -vv --debug fact windows_home

    # Create a directory
    pyinfra @winrm/192.168.3.232 --user vagrant \\
        --password vagrant --port 5985 windows_files.windows_directory 'c:\temp'

    # Run a powershell command ('ps' is the default shell-executable for the winrm connector)
    pyinfra @winrm/192.168.3.232 --user vagrant \\
        --password vagrant --port 5985 exec -- write-host hello

    # Run a command using the command prompt:
    pyinfra @winrm/192.168.3.232 --user vagrant \\
        --password vagrant --port 5985 --shell-executable cmd exec -- date /T

    # Run a command using the winrm ntlm transport
    pyinfra @winrm/192.168.3.232 --user vagrant \\
        --password vagrant --port 5985 --winrm-transport ntlm exec -- hostname
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import base64
import ntpath

import click
from typing_extensions import TypedDict, Unpack

from pyinfra import logger
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import get_file_io, memoize, sha1_hash

from pyinfra.connectors.base import BaseConnector, DataMeta
from pyinfra.connectors.util import read_output_buffers
from .pyinfrawinrmsession import PyinfraWinrmSession
from .util import make_win_command

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments


class ConnectorData(TypedDict):
    winrm_hostname: str
    port: int
    winrm_user: str
    password: str
    transport: str
    read_timeout_sec: int
    operation_timeout_sec: int


connector_data_meta: dict[str, DataMeta] = {
    "winrm_hostname": DataMeta("WinRM hostname to connect to"),
    "port": DataMeta("WinRM port to connect to"),
    "winrm_user": DataMeta("WinrRM username"),
    "password": DataMeta("WinRM password"),
    "transport": DataMeta("WinRM transport"),
    "read_timeout_sec": DataMeta("Read timeout in seconds"),
    "operation_timeout_sec": DataMeta("Operation timeout in seconds"),
}


def _raise_connect_error(host, message, data):
    message = "{0} ({1})".format(message, data)
    raise ConnectError(message)


@memoize
def show_warning():
    logger.warning("The @winrm connector is alpha!")


def _make_winrm_kwargs(state, host):
    kwargs = {}
    for key, value in (
        ("hostname", host.data.get("winrm_hostname")),
        ("username", host.data.get("ssh_user")),
        ("password", host.data.get("ssh_password")),
        ("port", int(host.data.get("port", 0))),
        ("winrm_transport", host.data.get("transport", "plaintext")),
        (
            "winrm_read_timeout_sec",
            host.data.get("read_timeout_sec", 30),
        ),
        (
            "winrm_operation_timeout_sec",
            host.data.get("operation_timeout_sec", 20),
        ),
    ):
        if value:
            kwargs[key] = value

    # FUTURE: add more auth
    # pywinrm supports: basic, certificate, ntlm, kerberos, plaintext, ssl, credssp
    # see https://github.com/diyan/pywinrm/blob/master/winrm/__init__.py#L12

    return kwargs


class WinRMConnector(BaseConnector):
    handles_execution = True

    session = None

    data: ConnectorData
    data_cls = ConnectorData
    data_meta = connector_data_meta

    @staticmethod
    def make_names_data(hostname):
        show_warning()

        yield "@winrm/{0}".format(hostname), {"winrm_hostname": hostname}, []

    def connect(self):
        """
        Connect to a single host. Returns the winrm Session if successful.
        """
        kwargs = _make_winrm_kwargs(self.state, self.host)
        logger.debug("Connecting to: %s (%s)", self.host.name, kwargs)

        # Hostname can be provided via winrm config (alias), data, or the hosts name
        hostname = kwargs.pop(
            "hostname",
        )

        try:
            # Create new session
            port = self.host.data.get("port", 5986)
            winrm_target = "{}".format(hostname)
            logger.debug("winrm_target: %s", winrm_target)
            logger.debug("winrm_user: %s", kwargs["username"])

            session = PyinfraWinrmSession(
                winrm_target,
                auth=(
                    kwargs["username"],
                    kwargs["password"],
                ),
                transport=kwargs["winrm_transport"],
                read_timeout_sec=kwargs["winrm_read_timeout_sec"],
                operation_timeout_sec=kwargs["winrm_operation_timeout_sec"],
            )
            self.session = session
            return session

        # TODO: add exceptions here
        except Exception as e:
            auth_kwargs = {}

            for key, value in kwargs.items():
                if key in ("username", "password"):
                    auth_kwargs[key] = value

            auth_args = ", ".join(
                "{0}={1}".format(key, value) for key, value in auth_kwargs.items()
            )
            logger.debug("%s", e)
            _raise_connect_error(self.host, "Authentication error", auth_args)

    def run_shell_command(
        self,
        command,
        print_output=False,
        print_input=False,
        **arguments: Unpack["ConnectorArguments"],
    ):
        """
        Execute a command on the specified host.

        Args:
            command (str): actual command to execute.
            print_output (bool): print the output.
            print_intput (bool): print the input.

        Keyword Args:
            _env (Mapping[str, str]): Dictionary of environment variables to set.
            _shell_executable (str): The shell executable to use for executing commands.
            _success_exit_codes Iterable[int]: List of exit codes to consider a success.

        Returns:
            tuple: (exit_code, stdout, stderr)
            stdout and stderr are both lists of strings from each buffer.
        """
        env = arguments.pop("_env", {})
        shell_executable = arguments.pop("_shell_executable", None)
        success_exit_codes = arguments.pop("_success_exit_codes", None)

        # TODO implement
        # * shell control features:
        # https://docs.pyinfra.com/en/3.x/arguments.html#shell-control-features
        # _chdir, _timeout, _get_pty, and _stdin

        # * privilege & user escalation:
        # https://docs.pyinfra.com/en/3.x/arguments.html#privilege-user-escalation

        command = make_win_command(command)

        logger.debug("Running command on %s: %s", self.host.name, command)

        if print_input:
            click.echo("{0}>>> {1}".format(self.host.print_prefix, command), err=True)

        # get rid of leading/trailing quote
        tmp_command = command.strip("'")

        if print_output:
            click.echo(
                "{0}>>> {1}".format(self.host.print_prefix, command),
                err=True,
            )

        if not shell_executable:
            shell_executable = "ps"
        logger.debug("shell_executable:%s", shell_executable)

        # we use our own subclassed session that allows for env setting from open_shell.
        if shell_executable in ["cmd"]:
            response = self.session.run_cmd(tmp_command, env=env)  # type: ignore
        else:
            response = self.session.run_ps(tmp_command, env=env)  # type: ignore

        return_code = response.status_code
        logger.debug("response:%s", response)

        std_out_str = response.std_out.decode("utf-8")
        std_err_str = response.std_err.decode("utf-8")

        # split on '\r\n' (windows newlines)
        std_out = std_out_str.split("\r\n")
        std_err = std_err_str.split("\r\n")

        logger.debug("std_out:%s", std_out)
        logger.debug("std_err:%s", std_err)

        if print_output:
            click.echo(
                "{0}>>> {1}".format(self.host.print_prefix, "\n".join(std_out)),
                err=True,
            )
        if success_exit_codes:
            status = return_code in success_exit_codes
        else:
            status = return_code == 0

        logger.debug("Command exit status: %s", status)

        combined_output = read_output_buffers(
            std_out,
            std_err,
            timeout=None,  # TODO need to take timeout in
            print_output=print_output,
            print_prefix=self.host.print_prefix,
        )
        return status, combined_output

    def get_file(
        state,
        host,
        remote_filename,
        filename_or_io,
        remote_temp_filename=None,
        **command_kwargs,
    ):
        raise PyinfraError("Not implemented")

    def _put_file(self, filename_or_io, remote_location, chunk_size=2048):
        # this should work fine on smallish files, but there will be perf issues
        # on larger files both due to the full read, the base64 encoding, and
        # the latency when sending chunks
        with get_file_io(filename_or_io) as file_io:
            data = file_io.read()
            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                ps = (
                    '$data = [System.Convert]::FromBase64String("{0}"); '
                    '{1} -Value $data -Encoding byte -Path "{2}"'
                ).format(
                    base64.b64encode(chunk).decode("utf-8"),
                    "Set-Content" if i == 0 else "Add-Content",
                    remote_location,
                )
                status, _stdout, stderr = self.run_shell_command(ps)
                if status is False:
                    logger.error("File upload error: {0}".format("\n".join(stderr)))
                    return False

        return True

    def put_file(
        self,
        filename_or_io,
        remote_filename,
        print_output=False,
        print_input=False,
        remote_temp_filename=None,  # ignored
        **command_kwargs,
    ):
        """
        Upload file by chunking and sending base64 encoded via winrm
        """

        # TODO: fix this? Workaround for circular import
        from pyinfra_windows.facts.files import TempDir

        # Always use temp file here in case of failure
        temp_file = ntpath.join(
            self.host.get_fact(TempDir),
            "pyinfra-{0}".format(sha1_hash(remote_filename)),
        )

        if not self._put_file(filename_or_io, temp_file):
            return False

        # Execute run_shell_command w/sudo and/or su_user
        command = "Move-Item -Path {0} -Destination {1} -Force".format(
            temp_file, remote_filename
        )
        status, _, stderr = self.run_shell_command(
            command,
            print_output=print_output,
            print_input=print_input,
            **command_kwargs,
        )

        if status is False:
            logger.error("File upload error: {0}".format("\n".join(stderr)))
            return False

        if print_output:
            click.echo(
                "{0}file uploaded: {1}".format(self.host.print_prefix, remote_filename),
                err=True,
            )

        return True
