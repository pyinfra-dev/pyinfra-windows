from unittest import TestCase
from unittest.mock import MagicMock, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all

from .util import make_inventory


class TestWinrmConnector(TestCase):
    def setUp(self):
        self.fake_connect_patch = patch(
            "pyinfra_windows.connectors.winrm.WinRMConnector.connect"
        )
        self.fake_connect_mock = self.fake_connect_patch.start()

    def tearDown(self):
        self.fake_connect_patch.stop()

    def test_connect_host(self):
        inventory = make_inventory(hosts=[("@winrm/somehost", {})])
        state = State(inventory, Config())
        host = inventory.get_host("@winrm/somehost")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0
        assert host.data.winrm_hostname == "somehost"

    def test_connect_all_password(self):
        inventory = make_inventory(
            hosts=(
                (
                    "@winrm/somehost",
                    {"winrm_username": "testuser", "winrm_password": "testpass"},
                ),
                (
                    "@winrm/anotherhost",
                    {"winrm_username": "testuser2", "winrm_password": "testpass2"},
                ),
            ),
        )
        state = State(inventory, Config())
        connect_all(state)

        # Get a host
        somehost = inventory.get_host("@winrm/somehost")
        assert somehost.data.winrm_username == "testuser"
        assert somehost.data.winrm_password == "testpass"

        assert len(state.active_hosts) == 2

    @patch("pyinfra_windows.connectors.winrm.PyinfraWinrmSession")
    def test_run_shell_command(self, fake_winrm_session):
        p = patch("pyinfra_windows.connectors.winrm.WinRMConnector.session")
        fake_session = p.start()

        fake_resp = MagicMock()
        fake_resp.status_code = 1
        fake_session.run_ps.return_value = fake_resp
        inventory = make_inventory(hosts=("@winrm/somehost",))
        State(inventory, Config())
        host = inventory.get_host("@winrm/somehost")
        host.connect()

        command = "echo hi"

        out = host.run_shell_command(
            command, print_output=True, _stdin="hello", _success_exit_codes=[1]
        )
        assert len(out) == 2

        status, output = out
        assert status is True

        combined_out = host.run_shell_command(
            command,
            print_output=True,
        )
        assert len(combined_out) == 2
        fake_session.run_ps.assert_called_with("echo hi", env={})
