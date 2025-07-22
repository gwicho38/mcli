# MCLI Cron Manager

A standalone cron job manager for scheduling MCLI commands to run automatically using the host OS cron system.

## Overview

The MCLI Cron Manager allows you to schedule any MCLI command created by the API decorator to run as a cron service under the underlying host OS. This provides a powerful way to automate MCLI workflows and tasks.

## Features

- ✅ **Schedule MCLI Commands**: Schedule any MCLI command to run automatically
- ✅ **Cron Expression Validation**: Built-in validation for cron schedule expressions
- ✅ **Wrapper Script Generation**: Automatic generation of executable wrapper scripts
- ✅ **Job Management**: Add, remove, list, and manage cron jobs
- ✅ **System Integration**: Direct integration with host OS crontab
- ✅ **Logging**: Comprehensive logging of job execution
- ✅ **Daemon Integration**: Works with the MCLI API daemon for command execution

## Installation

The cron manager is a standalone Python script that doesn't require installation into the main MCLI application to avoid recursion issues.

```bash
# Make the script executable
chmod +x cron_manager.py

# Test the installation
python cron_manager.py --help
```

## Usage

### Basic Commands

```bash
# Show help
python cron_manager.py --help

# List all cron jobs
python cron_manager.py list-jobs

# Show cron schedule examples
python cron_manager.py examples

# Validate a cron schedule
python cron_manager.py validate "0 2 * * *"
```

### Adding Cron Jobs

```bash
# Add a cron job
python cron_manager.py add <job-name> <command-name> <schedule> [options]

# Examples:
python cron_manager.py add "daily-backup" "backup" "0 2 * * *" --description "Daily backup at 2 AM"
python cron_manager.py add "status-check" "status" "*/5 * * * *" --args "verbose" --description "Check status every 5 minutes"
python cron_manager.py add "weekly-report" "report" "0 9 * * 1" --args "weekly" "pdf" --description "Generate weekly report on Mondays"
```

### Managing Jobs

```bash
# List all jobs
python cron_manager.py list-jobs

# Show details of a specific job
python cron_manager.py show <job-id>

# Remove a job
python cron_manager.py remove <job-id>

# Install all jobs to system crontab
python cron_manager.py install
```

## Cron Schedule Examples

### Common Patterns

```bash
*/5 * * * *     # Every 5 minutes
0 */2 * * *     # Every 2 hours
0 2 * * *       # Daily at 2 AM
0 9 * * 1-5     # Weekdays at 9 AM
0 0 1 * *       # Monthly on the 1st
0 0 * * 0       # Weekly on Sunday
```

### Specific Times

```bash
30 14 * * *     # Daily at 2:30 PM
0 8,12,18 * * * # Daily at 8 AM, 12 PM, 6 PM
0 9 * * 1       # Mondays at 9 AM
```

### Complex Patterns

```bash
0 9-17 * * 1-5  # Weekdays, 9 AM to 5 PM
0 0 1,15 * *    # 1st and 15th of each month
*/30 9-17 * * 1-5 # Every 30 minutes, weekdays 9-5
```

## Architecture

### Components

1. **CronManager Class**: Core job management functionality
2. **CronJob Dataclass**: Represents individual cron jobs
3. **Wrapper Scripts**: Bash scripts that execute MCLI commands
4. **JSON Storage**: Persistent job storage in `~/.local/mcli/cron/jobs.json`

### File Structure

```
~/.local/mcli/cron/
├── jobs.json                    # Job definitions
├── job_<uuid>.sh              # Wrapper scripts
└── ...
```

### Wrapper Script Example

```bash
#!/bin/bash
# MCLI Cron Job: test-job
# Job ID: 66161806-a713-4472-9ff7-c86a2cbf6cc4
# Command: status
# Created: 2025-07-22T03:29:53.712857

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="/Users/lefv"
export MCLI_DAEMON_ROUTING=true

# Log start
echo "[$(date)] Starting cron job: test-job"

# Execute command via daemon
python -m mcli workflow api-daemon execute --command-name status

# Log completion
echo "[$(date)] Completed cron job: test-job"
```

## Integration with MCLI API Daemon

The cron manager integrates with the MCLI API daemon to execute commands:

1. **Daemon Execution**: Commands are executed via the API daemon
2. **Environment Setup**: Proper environment variables are set
3. **Logging**: Comprehensive logging of job execution
4. **Error Handling**: Graceful handling of command failures

### Prerequisites

Before using the cron manager, ensure:

1. **API Daemon Running**: Start the MCLI API daemon
   ```bash
   python -m mcli workflow api-daemon start --background
   ```

2. **Command Available**: Verify the command exists in the daemon
   ```bash
   python -m mcli workflow api-daemon commands
   ```

## Examples

### Example 1: Daily Backup

```bash
# Add a daily backup job
python cron_manager.py add "daily-backup" "backup" "0 2 * * *" \
  --args "full" "compress" \
  --description "Daily full backup with compression"

# Install to crontab
python cron_manager.py install
```

### Example 2: Status Monitoring

```bash
# Add status monitoring every 5 minutes
python cron_manager.py add "status-monitor" "status" "*/5 * * * *" \
  --args "verbose" "health" \
  --description "Monitor system status every 5 minutes"

# List jobs
python cron_manager.py list-jobs
```

### Example 3: Weekly Reports

```bash
# Add weekly report generation
python cron_manager.py add "weekly-report" "report" "0 9 * * 1" \
  --args "weekly" "pdf" "email" \
  --description "Generate and email weekly report on Mondays"

# Show job details
python cron_manager.py show <job-id>
```

## Troubleshooting

### Common Issues

1. **Command Not Found**: Ensure the command exists in the API daemon
   ```bash
   python -m mcli workflow api-daemon commands
   ```

2. **Daemon Not Running**: Start the API daemon
   ```bash
   python -m mcli workflow api-daemon start --background
   ```

3. **Permission Issues**: Ensure wrapper scripts are executable
   ```bash
   chmod +x ~/.local/mcli/cron/job_*.sh
   ```

4. **Cron Not Working**: Check system cron service
   ```bash
   sudo systemctl status cron  # Linux
   sudo launchctl list | grep cron  # macOS
   ```

### Debugging

1. **Check Logs**: Monitor cron execution logs
   ```bash
   tail -f /tmp/mcli_cron.log
   ```

2. **Test Wrapper Script**: Manually test wrapper scripts
   ```bash
   ~/.local/mcli/cron/job_<uuid>.sh
   ```

3. **Verify Crontab**: Check system crontab
   ```bash
   crontab -l
   ```

## Security Considerations

1. **File Permissions**: Wrapper scripts are created with appropriate permissions
2. **Environment Isolation**: Jobs run with proper environment setup
3. **Logging**: All job executions are logged for audit purposes
4. **Validation**: Cron expressions are validated before creation

## Future Enhancements

- [ ] **Email Notifications**: Send email notifications on job completion/failure
- [ ] **Retry Logic**: Automatic retry on command failure
- [ ] **Dependencies**: Job dependency management
- [ ] **Web Interface**: Web-based job management interface
- [ ] **Metrics**: Job execution metrics and monitoring
- [ ] **Templates**: Predefined job templates for common tasks

## Contributing

The cron manager is designed to be standalone and avoid recursion issues with the main MCLI application. When contributing:

1. **Keep it Standalone**: Avoid dependencies on the main MCLI app
2. **Test Thoroughly**: Test all commands with various scenarios
3. **Document Changes**: Update this README for any new features
4. **Follow Patterns**: Use the existing patterns for consistency

## License

This cron manager is part of the MCLI project and follows the same licensing terms. 