# Testing Guide

This guide covers how to test the CETI data ingestion tools locally, including both S3 operations (using LocalStack) and whale tag workflows (using a Docker simulator).

## Whale Tag Simulator

The whale tag simulator allows you to test `ceti whaletag` commands locally without physical hardware.

### Quick Start

```bash
# Start the simulator
make whaletag-up

# Run automated tests
make test-whaletag

# Stop the simulator
make whaletag-down
```

### Manual Testing

```bash
# Start simulator
make whaletag-up

# Get container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456)

# Test SSH connection
ssh pi@$CONTAINER_IP
# Password: ceticeti

# Inside the container, check test data
ls -la /data

# Exit SSH
exit

# Test with ceti whaletag command
ceti whaletag -t $CONTAINER_IP

# Stop simulator
make whaletag-down
```

### What Gets Simulated

The simulator creates a Docker container with:
- **Base Image**: Alpine Linux (~12 MB)
- **Network**: Docker bridge network (container gets its own IP)
- **SSH Server**: OpenSSH on port 22
- **User**: `pi` with password `ceticeti`
- **Hostname**: `wt-b827eb123456` (configurable via `.env.whaletag`)
- **Test Data**: Sample files in `/data/`:
  - Audio files (`.raw`, `.flac`)
  - Sensor data (CSV files)

### Configuration

Edit `.env.whaletag` to customize:

```bash
# Hostname of the simulated whale tag
WHALETAG_HOSTNAME=wt-b827eb123456

# SSH password for user 'pi'
WHALETAG_PASSWORD=ceticeti

# Network mode (bridge, host, or macvlan)
NETWORK_MODE=bridge
```

**Network Modes:**
- **bridge** (default): Container gets Docker bridge IP, accessible from host via container IP
- **host**: Container shares host network (may conflict with host SSH on port 22)
- **macvlan** (advanced): Container gets real LAN IP via DHCP, discoverable by `ceti whaletag -l` from other machines

### Whale Tag Test Coverage

The whale tag integration tests verify:
- SSH connection to simulated tag
- Hostname pattern validation (`wt-*`)
- `/data` directory exists
- Test files present in `/data`
- SFTP file download
- User permissions for `pi` user

### Limitations

**What the simulator CAN test:**
- SSH/SFTP connectivity
- File download workflows (`ceti whaletag -t <IP>`)
- Hostname validation
- Data cleaning operations

**What the simulator CANNOT test (bridge mode):**
- Network discovery (`ceti whaletag -l` won't find containers on Docker bridge network)
- Real sensor data capture
- Actual whale tag firmware behavior
- Hardware-specific features

**Note:** In bridge mode (default), you must use `ceti whaletag -t <container-ip>` to connect directly. The `-l` discovery flag scans your LAN and won't find Docker bridge containers. For LAN discovery testing, use macvlan mode (see `.env.whaletag` configuration).

### Whale Tag Troubleshooting

**Simulator won't start:**
```bash
# Check Docker is running
docker ps

# View simulator logs
docker logs wt-b827eb123456
```

**Cannot connect via SSH:**
```bash
# Ensure simulator is running
docker ps | grep wt-b827eb123456

# Get container IP
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456

# Check SSH server status inside container
docker exec wt-b827eb123456 ps aux | grep sshd
```

**Clean start:**
```bash
# Remove all simulator data and restart
make whaletag-clean
make whaletag-up
```

### Advanced Whale Tag Usage

**Access simulator shell:**
```bash
docker exec -it wt-b827eb123456 /bin/bash
```

**View container logs:**
```bash
docker logs wt-b827eb123456
```

**Inspect test data:**
```bash
docker exec wt-b827eb123456 ls -la /data
```

**Test whale tag commands:**
```bash
# Get container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456)

# Download data from tag
ceti whaletag -t $CONTAINER_IP

# Clean tag (destructive - removes all /data files)
ceti whaletag -ct $CONTAINER_IP
```

## LocalStack S3 Testing

The project uses **LocalStack** to emulate AWS S3 locally, allowing you to test S3 operations without real AWS credentials.

### Quick Start

```bash
# One-time setup
docker pull localstack/localstack

# Run tests
make test-local
```

That's it! The `make test-local` command:
1. Starts LocalStack in Docker
2. Sets up test environment variables
3. Runs pytest
4. Stops LocalStack

### Manual LocalStack Testing

```bash
# Create and activate virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .[test]

# Start LocalStack
make localstack-up

# Load environment variables and run tests
set -a && source .env.localstack && set +a && pytest

# Or run specific tests
set -a && source .env.localstack && set +a && pytest tests/test_s3upload.py -v

# Stop LocalStack
make localstack-down

# Clean LocalStack data
make localstack-clean
```

## Testing Against Real AWS (Optional)

If you have AWS credentials configured, you can run tests against real AWS S3:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests WITHOUT LocalStack environment variables
pytest

# Tests will use your AWS credentials from ~/.aws/credentials
# and connect to real AWS S3
```

**Important:** Make sure `AWS_ENDPOINT_URL` is NOT set:
```bash
# Check if variable is set
echo $AWS_ENDPOINT_URL

# Unset if needed
unset AWS_ENDPOINT_URL

# Or start a fresh shell
exit  # then reopen terminal
```

## Production Workflow (Unchanged)

Field researchers continue using real AWS as before:

```bash
# Configure AWS credentials (one-time setup)
aws configure

# Authenticate to CodeArtifact
make login

# Use CLI tools as normal
ceti whaletag -a
ceti s3upload ./data
```

**No changes required!** The code automatically uses real AWS when `AWS_ENDPOINT_URL` is not set.

## Environment Variables

### Local Testing (LocalStack)

Set in `.env.localstack`:

```bash
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=cetitest
AWS_SECRET_ACCESS_KEY=cetitest
AWS_REGION=us-east-1
CETI_BUCKET=ceti-data-test
```

### Production

Uses standard AWS credential chain (no `.env` file needed):
1. `~/.aws/credentials` (from `aws configure`)
2. Environment variables (if set)
3. IAM roles (on EC2/ECS)

## Test Structure

### Unit Tests

Located in `tests/test_s3upload.py`:
- File discovery (`test_get_filelist`)
- S3 upload logic (`test_file_upload`)

### Integration Tests

Located in `tests/test_integration_*.py`:
- Hash-based deduplication
- End-to-end upload workflows
- Device ID validation
- Epoch timestamp renaming

### Whale Tag Integration Tests

Located in `tests/test_whaletag_integration.py`:
- SSH connection to simulated tag
- Hostname pattern validation
- Data directory validation
- SFTP file download
- User permissions

### Test Fixtures

Defined in `tests/conftest.py`:
- `s3_client` - Boto3 S3 client (LocalStack or real AWS)
- `test_bucket` - Test bucket with automatic creation/cleanup
- Session-scoped fixtures for performance

## Running Specific Tests

```bash
# Run all tests (excludes whale tag tests by default)
pytest

# Run only whale tag tests
pytest -m whaletag

# Run all tests including whale tag
pytest -m ""

# Run specific test file
pytest tests/test_s3upload.py

# Run specific test function
pytest tests/test_s3upload.py::test_get_filelist

# Run with verbose output
pytest -v

# Run with output capture disabled
pytest -s
```

## LocalStack Limitations

LocalStack Free Tier supports S3 and other basic AWS services, which is sufficient for testing the data ingestion tools.

**Supported with LocalStack:**
- ✅ `ceti s3upload` - S3 upload with deduplication
- ✅ `ceti general_offload` - File offloading and S3 upload
- ✅ All pytest S3 tests

**Not supported (requires real AWS or LocalStack Pro):**
- ❌ `ceti datapipeline` - Requires EMR (Elastic MapReduce)
- ❌ EMR cluster operations

If you try to run `ceti datapipeline` with LocalStack, you'll see:
```
ClientError: The API for service 'emr' is either not included in your current
license plan or has not yet been emulated by LocalStack.
```

**Solution:** Use real AWS credentials (not LocalStack) to test EMR/datapipeline functionality.

## Troubleshooting

### LocalStack not starting

```bash
# Check if LocalStack is running
docker ps | grep localstack

# Check logs
docker-compose -f docker-compose.localstack.yml logs

# Restart LocalStack
make localstack-down
make localstack-up
```

### Tests failing with connection errors

```bash
# Ensure LocalStack is accessible
curl http://localhost:4566/_localstack/health

# Check AWS_ENDPOINT_URL is set
echo $AWS_ENDPOINT_URL
```

### Port 4566 already in use

```bash
# Find process using port 4566
lsof -i :4566

# Stop existing LocalStack
make localstack-down
```

## Writing New Tests

### S3 Tests

When adding new tests that interact with S3:

```python
def test_my_feature(s3_client, test_bucket):
    """Test description"""
    # Use s3_client fixture (automatically points to LocalStack)
    s3_client.put_object(
        Bucket=test_bucket,
        Key='test-key',
        Body=b'test-data'
    )

    # Your test logic here
    result = my_function(s3_client, test_bucket)

    assert result == expected
```

The fixtures handle:
- Creating S3 client with correct endpoint
- Creating test bucket
- Cleaning up after tests

### Whale Tag Tests

When adding whale tag tests, use the `@pytest.mark.whaletag` marker:

```python
@pytest.mark.whaletag
def test_my_whale_tag_feature(ssh_client):
    """Test description"""
    # ssh_client fixture provides authenticated connection
    stdin, stdout, stderr = ssh_client.exec_command('ls /data')
    files = stdout.read().decode().strip().split('\n')

    assert len(files) > 0
```

## Additional Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [pytest Documentation](https://docs.pytest.org/)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
