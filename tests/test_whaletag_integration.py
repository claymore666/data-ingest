"""
Whale Tag Integration Tests

These tests require a whale tag simulator or real hardware to be available.
They are excluded from default pytest runs via pytest markers.

To run these tests:
  make test-whaletag  # Starts simulator, runs tests, stops simulator
  pytest -m whaletag  # Run with existing simulator/hardware
"""

import os
import pytest
import paramiko


# Whale tag connection parameters
# For simulator: get IP with docker inspect
WHALETAG_HOSTNAME = os.getenv('WHALETAG_HOSTNAME', 'wt-b827eb123456')
WHALETAG_HOST = os.getenv('WHALETAG_HOST')  # If not set, will auto-detect from Docker
WHALETAG_PORT = int(os.getenv('WHALETAG_PORT', '22'))  # Standard SSH port
WHALETAG_USERNAME = 'pi'
WHALETAG_PASSWORD = os.getenv('WHALETAG_PASSWORD', 'ceticeti')
WHALETAG_HOSTNAME_PATTERN = r'^wt-[a-z0-9]{6,}$'


def get_whaletag_ip():
    """Get IP address of whale tag simulator container"""
    if WHALETAG_HOST:
        return WHALETAG_HOST

    # Auto-detect container IP
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'inspect', '-f',
             '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
             WHALETAG_HOSTNAME],
            capture_output=True, text=True, check=True
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except subprocess.CalledProcessError:
        pass

    raise RuntimeError(
        f"Cannot find whale tag simulator. "
        f"Set WHALETAG_HOST or ensure container '{WHALETAG_HOSTNAME}' is running."
    )


@pytest.fixture
def ssh_client():
    """Create SSH client connection to whale tag"""
    host = get_whaletag_ip()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=WHALETAG_PORT,
        username=WHALETAG_USERNAME,
        password=WHALETAG_PASSWORD,
        timeout=10
    )
    yield client
    client.close()


@pytest.mark.whaletag
def test_ssh_connection(ssh_client):
    """Test SSH connection to whale tag"""
    stdin, stdout, stderr = ssh_client.exec_command('echo "test"')
    output = stdout.read().decode().strip()
    assert output == 'test', "SSH command execution failed"


@pytest.mark.whaletag
def test_hostname_pattern(ssh_client):
    """Test that hostname matches wt-* pattern"""
    import re
    stdin, stdout, stderr = ssh_client.exec_command('hostname')
    hostname = stdout.read().decode().strip()
    assert re.match(WHALETAG_HOSTNAME_PATTERN, hostname), \
        f"Hostname '{hostname}' does not match pattern '{WHALETAG_HOSTNAME_PATTERN}'"


@pytest.mark.whaletag
def test_data_directory_exists(ssh_client):
    """Test that /data directory exists"""
    stdin, stdout, stderr = ssh_client.exec_command('test -d /data && echo "exists"')
    output = stdout.read().decode().strip()
    assert output == 'exists', "/data directory does not exist"


@pytest.mark.whaletag
def test_data_directory_has_files(ssh_client):
    """Test that /data directory contains test files"""
    stdin, stdout, stderr = ssh_client.exec_command('ls -1 /data')
    files = stdout.read().decode().strip().split('\n')
    assert len(files) > 0, "/data directory is empty"
    assert any('audio' in f or 'sensor' in f for f in files), \
        "Expected test files (audio, sensors) not found in /data"


@pytest.mark.whaletag
def test_sftp_download(ssh_client):
    """Test SFTP file download from whale tag"""
    import tempfile
    from pathlib import Path

    sftp = ssh_client.open_sftp()

    # List files in /data
    files = sftp.listdir('/data')
    assert len(files) > 0, "/data directory is empty"

    # Download first file
    remote_file = f'/data/{files[0]}'

    with tempfile.TemporaryDirectory() as tmpdir:
        local_file = Path(tmpdir) / files[0]
        sftp.get(remote_file, str(local_file))
        assert local_file.exists(), f"Failed to download {remote_file}"
        assert local_file.stat().st_size >= 0, "Downloaded file is invalid"

    sftp.close()


@pytest.mark.whaletag
def test_user_permissions(ssh_client):
    """Test that user pi can access /data directory"""
    stdin, stdout, stderr = ssh_client.exec_command('whoami')
    user = stdout.read().decode().strip()
    assert user == 'pi', f"Expected user 'pi', got '{user}'"

    # Test write permission
    stdin, stdout, stderr = ssh_client.exec_command('touch /data/.test && rm /data/.test && echo "success"')
    output = stdout.read().decode().strip()
    assert output == 'success', "User pi does not have write permission to /data"
