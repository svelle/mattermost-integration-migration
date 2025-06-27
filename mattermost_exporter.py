#!/usr/bin/env python3
"""
Mattermost Integration Exporter

A tool to export and import Mattermost webhooks and bot data using the Mattermost REST API.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class MattermostClient:
    """Client for interacting with the Mattermost REST API"""
    
    def __init__(self, server_url: str, token: str):
        self.server_url = server_url.rstrip('/')
        self.api_url = f"{self.server_url}/api/v4"
        self.token = token
        self.session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to API endpoint"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make POST request to API endpoint"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make PUT request to API endpoint"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint: str) -> bool:
        """Make DELETE request to API endpoint"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.status_code == 200


class MattermostExporter:
    """Main exporter class for handling Mattermost integrations"""
    
    def __init__(self, client: MattermostClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
    
    def export_incoming_webhooks(self) -> List[Dict]:
        """Export all incoming webhooks"""
        self.logger.info("Exporting incoming webhooks...")
        try:
            webhooks = self.client.get("hooks/incoming")
            self.logger.info(f"Found {len(webhooks)} incoming webhooks")
            print(f"📥 Found {len(webhooks)} incoming webhook(s)")
            for webhook in webhooks:
                name = webhook.get('display_name', 'Unnamed')
                print(f"  ✓ {name}")
            return webhooks
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to export incoming webhooks: {e}")
            print(f"📥 ✗ Failed to export incoming webhooks: {e}")
            return []
    
    def export_outgoing_webhooks(self) -> List[Dict]:
        """Export all outgoing webhooks"""
        self.logger.info("Exporting outgoing webhooks...")
        try:
            webhooks = self.client.get("hooks/outgoing")
            self.logger.info(f"Found {len(webhooks)} outgoing webhooks")
            print(f"📤 Found {len(webhooks)} outgoing webhook(s)")
            for webhook in webhooks:
                name = webhook.get('display_name', 'Unnamed')
                print(f"  ✓ {name}")
            return webhooks
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to export outgoing webhooks: {e}")
            print(f"📤 ✗ Failed to export outgoing webhooks: {e}")
            return []
    
    def export_bots(self) -> List[Dict]:
        """Export all bot accounts"""
        self.logger.info("Exporting bot accounts...")
        try:
            bots = self.client.get("bots")
            self.logger.info(f"Found {len(bots)} bot accounts")
            print(f"🤖 Found {len(bots)} bot account(s)")
            for bot in bots:
                name = bot.get('username', 'Unnamed')
                display_name = bot.get('display_name', '')
                name_display = f"{name} ({display_name})" if display_name and display_name != name else name
                print(f"  ✓ {name_display}")
            return bots
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to export bot accounts: {e}")
            print(f"🤖 ✗ Failed to export bot accounts: {e}")
            return []
    
    
    def export_all(self, output_file: str):
        """Export all webhooks and bots to JSON file"""
        self.logger.info("Starting full export...")
        print(f"🔄 Starting export from {self.client.server_url}...")
        
        # Test connection first
        try:
            user_info = self.client.get("users/me")
            print(f"✓ Connected as: {user_info.get('username', 'Unknown')}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Mattermost server: {e}")
            print(f"✗ Connection failed: Unable to connect to {self.client.server_url}")
            print("Please check your MATTERMOST_SERVER_URL and MATTERMOST_TOKEN")
            sys.exit(1)
        
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'server_url': self.client.server_url,
                'version': '1.0'
            },
            'incoming_webhooks': self.export_incoming_webhooks(),
            'outgoing_webhooks': self.export_outgoing_webhooks(),
            'bots': self.export_bots()
        }
        
        # Check if any exports failed completely
        if (not export_data['incoming_webhooks'] and 
            not export_data['outgoing_webhooks'] and 
            not export_data['bots']):
            # Check if this is due to connection issues
            try:
                self.client.get("users/me")
                # Connection works, just no data
                pass
            except requests.exceptions.RequestException:
                print("✗ Export failed: Connection issues prevented data retrieval")
                sys.exit(1)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            total_items = (len(export_data['incoming_webhooks']) + 
                          len(export_data['outgoing_webhooks']) + 
                          len(export_data['bots']))
            
            self.logger.info(f"Export completed successfully. {total_items} items exported to {output_file}")
            print(f"✓ Export completed: {total_items} items saved to {output_file}")
            
        except IOError as e:
            self.logger.error(f"Failed to write export file: {e}")
            print(f"✗ Export failed: {e}")
            sys.exit(1)
    
    def import_incoming_webhooks(self, webhooks: List[Dict], dry_run: bool = False):
        """Import incoming webhooks"""
        if not webhooks:
            return 0
            
        self.logger.info(f"Importing {len(webhooks)} incoming webhooks (dry_run={dry_run})")
        print(f"📥 Importing {len(webhooks)} incoming webhook(s)...")
        
        # Get existing webhooks to check for duplicates
        existing_webhooks = []
        if not dry_run:
            try:
                existing_webhooks = self.client.get("hooks/incoming")
            except requests.exceptions.RequestException:
                pass
        
        success_count = 0
        for webhook in webhooks:
            original_name = webhook.get('display_name', 'Unnamed')
            name = original_name
            
            try:
                # Remove server-generated fields
                webhook_data = {k: v for k, v in webhook.items() 
                               if k not in ['id', 'create_at', 'update_at', 'delete_at']}
                
                # Check for existing webhook with same name
                duplicate_found = False
                if not dry_run:
                    for existing in existing_webhooks:
                        if existing.get('display_name') == original_name:
                            duplicate_found = True
                            break
                
                # Modify webhook data for import
                if duplicate_found:
                    webhook_data['display_name'] = f"{original_name} (imported)"
                    name = webhook_data['display_name']
                
                # Add import note to description
                import_note = f"[Imported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
                existing_desc = webhook_data.get('description', '')
                if existing_desc:
                    webhook_data['description'] = f"{existing_desc}\n\n{import_note}"
                else:
                    webhook_data['description'] = import_note
                
                if not dry_run:
                    self.client.post("hooks/incoming", webhook_data)
                
                success_count += 1
                status_msg = f"  ✓ {name}"
                if duplicate_found:
                    status_msg += " (renamed to avoid conflict)"
                print(status_msg)
                self.logger.debug(f"Imported incoming webhook: {name}")
                
            except requests.exceptions.RequestException as e:
                print(f"  ✗ {name} - {e}")
                self.logger.error(f"Failed to import incoming webhook {name}: {e}")
        
        self.logger.info(f"Successfully imported {success_count}/{len(webhooks)} incoming webhooks")
        return success_count
    
    def import_outgoing_webhooks(self, webhooks: List[Dict], dry_run: bool = False):
        """Import outgoing webhooks"""
        if not webhooks:
            return 0
            
        self.logger.info(f"Importing {len(webhooks)} outgoing webhooks (dry_run={dry_run})")
        print(f"📤 Importing {len(webhooks)} outgoing webhook(s)...")
        
        # Get existing webhooks to check for duplicates
        existing_webhooks = []
        if not dry_run:
            try:
                existing_webhooks = self.client.get("hooks/outgoing")
            except requests.exceptions.RequestException:
                pass
        
        success_count = 0
        for webhook in webhooks:
            original_name = webhook.get('display_name', 'Unnamed')
            name = original_name
            
            try:
                # Remove server-generated fields
                webhook_data = {k: v for k, v in webhook.items() 
                               if k not in ['id', 'create_at', 'update_at', 'delete_at', 'token']}
                
                # Check for existing webhook with same name
                duplicate_found = False
                if not dry_run:
                    for existing in existing_webhooks:
                        if existing.get('display_name') == original_name:
                            duplicate_found = True
                            break
                
                # Modify webhook data for import
                if duplicate_found:
                    webhook_data['display_name'] = f"{original_name} (imported)"
                    name = webhook_data['display_name']
                
                # Add import note to description
                import_note = f"[Imported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
                existing_desc = webhook_data.get('description', '')
                if existing_desc:
                    webhook_data['description'] = f"{existing_desc}\n\n{import_note}"
                else:
                    webhook_data['description'] = import_note
                
                if not dry_run:
                    self.client.post("hooks/outgoing", webhook_data)
                
                success_count += 1
                status_msg = f"  ✓ {name}"
                if duplicate_found:
                    status_msg += " (renamed to avoid conflict)"
                print(status_msg)
                self.logger.debug(f"Imported outgoing webhook: {name}")
                
            except requests.exceptions.RequestException as e:
                print(f"  ✗ {name} - {e}")
                self.logger.error(f"Failed to import outgoing webhook {name}: {e}")
        
        self.logger.info(f"Successfully imported {success_count}/{len(webhooks)} outgoing webhooks")
        return success_count
    
    def import_bots(self, bots: List[Dict], dry_run: bool = False):
        """Import bot accounts"""
        if not bots:
            return 0
            
        self.logger.info(f"Importing {len(bots)} bot accounts (dry_run={dry_run})")
        print(f"🤖 Importing {len(bots)} bot account(s)...")
        
        success_count = 0
        for bot in bots:
            name = bot.get('username', 'Unnamed')
            try:
                # Remove server-generated fields and prepare bot data
                bot_data = {k: v for k, v in bot.items() 
                           if k not in ['user_id', 'create_at', 'update_at', 'delete_at', 'owner_id']}
                
                if not dry_run:
                    self.client.post("bots", bot_data)
                
                success_count += 1
                print(f"  ✓ {name}")
                self.logger.debug(f"Imported bot: {name}")
                
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if "403" in error_msg:
                    error_msg = "Insufficient permissions to create bots"
                elif "409" in error_msg:
                    error_msg = "Bot already exists"
                print(f"  ✗ {name} - {error_msg}")
                self.logger.error(f"Failed to import bot {name}: {e}")
        
        self.logger.info(f"Successfully imported {success_count}/{len(bots)} bot accounts")
        return success_count
    
    
    def import_all(self, input_file: str, dry_run: bool = False):
        """Import all webhooks and bots from JSON file"""
        self.logger.info(f"Starting import from {input_file} (dry_run={dry_run})")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to read import file: {e}")
            print(f"✗ Import failed: {e}")
            sys.exit(1)
        
        # Validate import data structure
        required_keys = ['incoming_webhooks', 'outgoing_webhooks', 'bots']
        for key in required_keys:
            if key not in import_data:
                self.logger.error(f"Invalid import file: missing '{key}' section")
                print(f"✗ Import failed: Invalid file format")
                sys.exit(1)
        
        if dry_run:
            print("🔍 Dry run mode - no changes will be made")
        
        # Import each type
        incoming_count = self.import_incoming_webhooks(import_data['incoming_webhooks'], dry_run)
        outgoing_count = self.import_outgoing_webhooks(import_data['outgoing_webhooks'], dry_run)
        bot_count = self.import_bots(import_data['bots'], dry_run)
        
        total_imported = incoming_count + outgoing_count + bot_count
        total_items = (len(import_data['incoming_webhooks']) + 
                      len(import_data['outgoing_webhooks']) + 
                      len(import_data['bots']))
        
        if dry_run:
            print(f"🔍 Dry run completed: {total_imported}/{total_items} items would be imported")
        else:
            print(f"✓ Import completed: {total_imported}/{total_items} items imported successfully")


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mattermost_exporter.log'),
            logging.StreamHandler(sys.stdout) if verbose else logging.NullHandler()
        ]
    )


def load_config():
    """Load configuration from environment variables or .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    server_url = os.getenv('MATTERMOST_SERVER_URL')
    token = os.getenv('MATTERMOST_TOKEN')
    
    if not server_url:
        print("✗ Error: MATTERMOST_SERVER_URL environment variable is required")
        sys.exit(1)
    
    if not token:
        print("✗ Error: MATTERMOST_TOKEN environment variable is required")
        sys.exit(1)
    
    return server_url, token


def main():
    parser = argparse.ArgumentParser(
        description='Export and import Mattermost webhooks and bot data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  MATTERMOST_SERVER_URL    Mattermost server URL (required)
  MATTERMOST_TOKEN         Personal access token or bot token (required)

Examples:
  %(prog)s export -o backup.json
  %(prog)s import -i backup.json --dry-run
  %(prog)s import -i backup.json
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export webhooks and bots')
    export_parser.add_argument('-o', '--output', default='mattermost_export.json',
                              help='Output file path (default: mattermost_export.json)')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import webhooks and bots')
    import_parser.add_argument('-i', '--input', required=True,
                              help='Input file path')
    import_parser.add_argument('--dry-run', action='store_true',
                              help='Preview changes without applying them')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Load configuration
    server_url, token = load_config()
    
    # Initialize client and exporter
    try:
        client = MattermostClient(server_url, token)
        exporter = MattermostExporter(client)
    except Exception as e:
        print(f"✗ Failed to initialize Mattermost client: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'export':
            exporter.export_all(args.output)
        elif args.command == 'import':
            exporter.import_all(args.input, args.dry_run)
    except KeyboardInterrupt:
        print("\n⚠ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Operation failed: {e}")
        logging.getLogger(__name__).exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == '__main__':
    main()