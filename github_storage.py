"""
GitHub Storage - Store and retrieve scan results from GitHub repository
Uses GitHub as a database/cache for scan results
"""
import json
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from config import Config


class GitHubStorage:
    """Manage scan results in GitHub repository"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub storage
        
        Args:
            github_token: GitHub personal access token (for push operations)
        """
        self.repo_owner = "Signal-Watch"
        self.repo_name = "signal-watch"
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.raw_base_url = f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/main"
        
        self.github_token = github_token or Config.GITHUB_TOKEN if hasattr(Config, 'GITHUB_TOKEN') else None
        
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def check_company_exists(self, company_number: str, folder_suffix: str = "Directors") -> bool:
        """
        Check if scan results exist for a company in GitHub
        
        Args:
            company_number: Company number to check
            folder_suffix: Folder name (Directors or Only Active Directors)
            
        Returns:
            True if results exist, False otherwise
        """
        file_path = f"results/{company_number}/{folder_suffix}/latest.json"
        url = f"{self.base_url}/contents/{file_path}"
        
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_company_data(self, company_number: str, folder_suffix: str = "Directors") -> Optional[Dict[str, Any]]:
        """
        Retrieve scan results for a company from GitHub
        
        Args:
            company_number: Company number
            folder_suffix: Folder name (Directors or Only Active Directors)
            
        Returns:
            Scan results dictionary or None if not found
        """
        file_path = f"results/{company_number}/{folder_suffix}/latest.json"
        url = f"{self.raw_base_url}/{file_path}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching data from GitHub: {e}")
            return None
    
    def push_company_data(self, company_number: str, results: Dict[str, Any]) -> bool:
        """
        Push scan results to GitHub repository
        
        Args:
            company_number: Company number
            results: Scan results dictionary (single company result)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_token:
            print("GitHub token not configured. Cannot push to repository.")
            return False
        
        # Prepare data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Folder structure determined by caller (passed via metadata)
        folder_suffix = results.get('_folder_type', 'Directors')
        
        file_path = f"results/{company_number}/{folder_suffix}/latest.json"
        archive_path = f"results/{company_number}/{folder_suffix}/{timestamp}.json"
        
        # Add metadata
        results['_metadata'] = {
            'company_number': company_number,
            'scanned_at': datetime.now().isoformat(),
            'scan_timestamp': timestamp,
            'version': '1.0'
        }
        
        # Convert to JSON
        content = json.dumps(results, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content.encode()).decode()
        
        # Check if file exists (to get SHA for update)
        sha = self._get_file_sha(file_path)
        
        # Prepare commit data
        commit_data = {
            'message': f'Add scan results for company {company_number}',
            'content': encoded_content,
            'branch': 'main'
        }
        
        if sha:
            commit_data['sha'] = sha  # Update existing file
        
        try:
            # Push latest.json
            url = f"{self.base_url}/contents/{file_path}"
            response = self.session.put(url, json=commit_data)
            
            if response.status_code in [200, 201]:
                print(f"✅ Pushed results to GitHub: {file_path}")
                
                # Also create archived version
                commit_data['message'] = f'Archive scan results for company {company_number} - {timestamp}'
                commit_data.pop('sha', None)  # Remove SHA for new file
                archive_url = f"{self.base_url}/contents/{archive_path}"
                self.session.put(archive_url, json=commit_data)
                
                return True
            else:
                print(f"❌ Failed to push to GitHub: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error pushing to GitHub: {e}")
            return False
    
    def _get_file_sha(self, file_path: str) -> Optional[str]:
        """Get SHA of existing file for updates"""
        url = f"{self.base_url}/contents/{file_path}"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json().get('sha')
        except:
            pass
        return None
    
    def list_available_companies(self) -> List[str]:
        """
        List all companies that have scan results in GitHub
        
        Returns:
            List of company numbers
        """
        url = f"{self.base_url}/contents/results"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                contents = response.json()
                # Each folder is a company number
                return [item['name'] for item in contents if item['type'] == 'dir']
        except Exception as e:
            print(f"Error listing companies: {e}")
        
        return []
    
    def get_company_history(self, company_number: str) -> List[Dict[str, Any]]:
        """
        Get all historical scans for a company
        
        Args:
            company_number: Company number
            
        Returns:
            List of scan metadata (timestamps, file names)
        """
        url = f"{self.base_url}/contents/results/{company_number}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                contents = response.json()
                scans = []
                for item in contents:
                    if item['name'].endswith('.json') and item['name'] != 'latest.json':
                        scans.append({
                            'filename': item['name'],
                            'timestamp': item['name'].replace('.json', ''),
                            'download_url': item['download_url'],
                            'size': item['size']
                        })
                return sorted(scans, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            print(f"Error getting company history: {e}")
        
        return []
    
    def push_file_to_github(self, file_path: str, local_file_path: str, commit_message: str) -> bool:
        """
        Push any file (PDF, CSV, ZIP, etc.) to GitHub
        
        Args:
            file_path: Path in GitHub repo (e.g., results/00081701/pdfs/file.pdf)
            local_file_path: Local file path to read
            commit_message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_token:
            return False
        
        try:
            # Read file and encode
            with open(local_file_path, 'rb') as f:
                content = f.read()
            encoded_content = base64.b64encode(content).decode()
            
            # Check if file exists
            sha = self._get_file_sha(file_path)
            
            commit_data = {
                'message': commit_message,
                'content': encoded_content,
                'branch': 'main'
            }
            
            if sha:
                commit_data['sha'] = sha
            
            url = f"{self.base_url}/contents/{file_path}"
            response = self.session.put(url, json=commit_data)
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            print(f"Error pushing file to GitHub: {e}")
            return False
