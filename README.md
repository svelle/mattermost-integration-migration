# Mattermost Integration Exporter

A Python tool to export and import Mattermost webhooks and bot data using the Mattermost REST API.

## Features

- Export incoming and outgoing webhooks
- Export bot accounts
- Import webhooks and bots with conflict handling
- Dry-run mode to preview changes
- JSON-based export format for portability
- Comprehensive logging and error handling
- Environment variable configuration

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Set the following environment variables or create a `.env` file:

```bash
MATTERMOST_SERVER_URL=https://your-mattermost-server.com
MATTERMOST_TOKEN=your-personal-access-token-or-bot-token
```

### Getting a Token

1. **Personal Access Token**: Go to Account Settings → Security → Personal Access Tokens
2. **Bot Token**: Create a bot account and use its token

## Usage

### Export Data

Export all webhooks and bots to a JSON file:

```bash
python mattermost_exporter.py export -o backup.json
```

### Import Data

Preview what would be imported (dry-run):

```bash
python mattermost_exporter.py import -i backup.json --dry-run
```

Import the data:

```bash
python mattermost_exporter.py import -i backup.json
```

### Command Line Options

```bash
# Export command
python mattermost_exporter.py export [-o OUTPUT_FILE]

# Import command  
python mattermost_exporter.py import -i INPUT_FILE [--dry-run]

# General options
python mattermost_exporter.py [-v|--verbose] COMMAND
```

## Export Format

The tool creates JSON files with the following structure:

```json
{
  "metadata": {
    "export_date": "2024-01-01T12:00:00",
    "server_url": "https://your-mattermost-server.com",
    "version": "1.0"
  },
  "incoming_webhooks": [...],
  "outgoing_webhooks": [...],
  "bots": [...]
}
```

## Important Notes

- **Bot Tokens**: When importing bots, new access tokens will be generated
- **Webhook URLs**: Incoming webhook URLs will change after import
- **Permissions**: Ensure your token has sufficient permissions to create webhooks and bots
- **Server Fields**: Server-generated fields (IDs, timestamps) are automatically excluded during import

## Logging

The tool creates a log file `mattermost_exporter.log` with detailed operation information. Use the `-v` flag for verbose console output.

## Error Handling

- Network errors are automatically retried
- Invalid imports are validated before processing
- Individual item failures don't stop the entire operation
- Detailed error messages are logged for troubleshooting

## Requirements

- Python 3.6+
- Mattermost server with API access
- Valid authentication token with appropriate permissions# mattermost-integration-migration
