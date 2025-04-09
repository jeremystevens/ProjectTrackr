# FlaskBin Maintenance Guide

This document covers maintenance tasks for the FlaskBin application, including how to handle expired pastes and other routine operations.

## Pruning Expired Pastes

The application includes a pruning mechanism to automatically remove pastes that have reached their expiration date. This helps keep the database clean and ensures that pastes are actually deleted when they expire, not just hidden from view.

### How Expiration Works

1. When a paste is created, an expiration time may be set (10 minutes, 1 hour, 1 day, 1 month, or never).
2. When viewing pastes, the application checks if a paste has expired before displaying it.
3. However, expired pastes remain in the database until they are pruned.

### Pruning Options

There are three ways to prune expired pastes:

1. **Automatic Pruning (Recommended)**: Set up a cron job to run the prune script every 10 minutes.
2. **Manual Pruning**: Run the prune script manually whenever you want to clean up expired pastes.
3. **Dry Run**: Check which pastes would be pruned without actually deleting anything.

### Setting Up Automatic Pruning

To set up a cron job that prunes expired pastes every 10 minutes:

1. Make sure you have cron installed on your system.
2. Run the provided setup script:

```bash
./setup_prune_cron.sh
```

This will add a cron job that runs the prune script every 10 minutes. You can verify the installation by running `crontab -l`.

### Running a Manual Prune

To manually prune expired pastes:

```bash
./prune_now.sh
```

This will remove all pastes that have passed their expiration date.

### Running a Dry Run

To see what pastes would be pruned without actually deleting them:

```bash
python prune_expired.py --dry-run
```

This will list all the expired pastes that would be pruned but won't delete them.

## Prune Script Behavior

The prune script does the following:

1. Identifies all pastes with an expiration date that has passed
2. For each expired paste:
   - Deletes associated view records
   - Updates the author's paste and view counts if applicable
   - Deletes the paste from the database
3. Logs all operations for audit purposes

## Log Files

The prune script generates logs in the following files:

- `prune_expired.log`: Contains detailed information about each prune operation

## Troubleshooting

If you encounter issues with the prune script:

1. Check the log files for error messages
2. Make sure the script has the correct permissions
3. Verify that the database connection is working
4. If using cron, check that the cron service is running

## Other Maintenance Tasks

### Database Backup

It's recommended to regularly back up the PostgreSQL database to prevent data loss:

```bash
pg_dump $DATABASE_URL > flaskbin_backup_$(date +%Y%m%d).sql
```

### Log Rotation

To prevent log files from growing too large, consider setting up log rotation:

```bash
# Example logrotate configuration
cat > /etc/logrotate.d/flaskbin << EOF
/path/to/flaskbin/prune_expired.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```
