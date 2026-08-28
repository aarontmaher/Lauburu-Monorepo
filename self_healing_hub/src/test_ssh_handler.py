import unittest
from unittest.mock import patch, MagicMock
import subprocess
import os
import sys

# Ensure src directory is on sys.path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ssh_handler import SSHHandler

class TestSSHHandler(unittest.TestCase):
    def test_direct_ssh_command(self):
        handler = SSHHandler(host="100.73.38.87", username="u0_a363", port=8022, key_file="~/.ssh/id_ed25519")
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Linux pixel 5.10", stderr="")
            res = handler.run_cmd("uname -a")
            
            self.assertIsNotNone(res)
            self.assertEqual(res.returncode, 0)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            full_cmd = args[0]
            self.assertEqual(full_cmd[0], "ssh")
            self.assertIn("-p", full_cmd)
            self.assertIn("8022", full_cmd)
            self.assertIn("u0_a363@100.73.38.87", full_cmd)
            self.assertEqual(full_cmd[-1], "uname -a")

    def test_relay_ssh_command_without_single_quotes(self):
        handler = SSHHandler(
            host="192.168.8.224",
            username="linux",
            relay_host="100.122.185.123",
            relay_cmd="dbclient -y linux@192.168.8.224"
        )
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Linux headnode", stderr="")
            res = handler.run_cmd("uname -a")
            
            self.assertIsNotNone(res)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            full_cmd = args[0]
            self.assertTrue(full_cmd[0].endswith("ssh") or full_cmd[0].endswith("sshpass"))
            self.assertEqual(full_cmd[-2], "root@100.122.185.123")
            expected_remote_cmd = "DROPBEAR_PASSWORD='goldfighting1' dbclient -y linux@192.168.8.224 'uname -a'"
            self.assertEqual(full_cmd[-1], expected_remote_cmd)

    def test_relay_ssh_command_with_single_quotes(self):
        handler = SSHHandler(
            host="192.168.8.224",
            username="linux",
            relay_host="100.122.185.123",
            relay_cmd="dbclient -y linux@192.168.8.224"
        )
        
        # Test command with single quotes e.g. echo 'hello world'
        cmd_with_quotes = "echo 'hello world'"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello world", stderr="")
            res = handler.run_cmd(cmd_with_quotes)
            
            self.assertIsNotNone(res)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            full_cmd = args[0]
            # Single quote in cmd_with_quotes is replaced by '\''
            # So 'echo '\''hello world'\'''
            expected_remote_cmd = "DROPBEAR_PASSWORD='goldfighting1' dbclient -y linux@192.168.8.224 'echo '\\''hello world'\\'''"
            self.assertEqual(full_cmd[-1], expected_remote_cmd)

    def test_relay_ssh_command_complex_nested_quotes(self):
        handler = SSHHandler(
            host="192.168.8.224",
            username="linux",
            relay_host="100.122.185.123",
            relay_cmd="dbclient linux@192.168.8.224"
        )
        
        cmd_string = "DROPBEAR_PASSWORD='goldfighting1' dbclient -y linux@192.168.8.224 'uname -a'"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Linux headnode", stderr="")
            res = handler.run_cmd(cmd_string)
            
            self.assertIsNotNone(res)
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            full_cmd = args[0]
            
            # The single quotes inside cmd_string should be replaced with '\''
            expected_safe_cmd = "DROPBEAR_PASSWORD='\\''goldfighting1'\\'' dbclient -y linux@192.168.8.224 '\\''uname -a'\\''"
            expected_remote_cmd = f"DROPBEAR_PASSWORD='goldfighting1' dbclient -y linux@192.168.8.224 '{expected_safe_cmd}'"
            self.assertEqual(full_cmd[-1], expected_remote_cmd)

    def test_ssh_command_timeout(self):
        handler = SSHHandler(host="127.0.0.1")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=5)):
            res = handler.run_cmd("sleep 10", timeout=5)
            self.assertIsNone(res)

    def test_ssh_command_exception(self):
        handler = SSHHandler(host="127.0.0.1")
        with patch("subprocess.run", side_effect=Exception("Connection failed")):
            res = handler.run_cmd("ls")
            self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
