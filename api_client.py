"""
Companies House API Client
Handles all interactions with the Companies House API
"""
import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import Config
from .rate_limiter import RateLimiter


class CompaniesHouseClient:
    """Client for Companies House API with rate limiting and caching"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            api_key: Companies House API key (uses config if not provided)
        """
        self.api_key = api_key or Config.COMPANIES_HOUSE_API_KEY
        if not self.api_key:
            raise ValueError("API key required. Set COMPANIES_HOUSE_API_KEY in .env")
        
        self.base_url = Config.CH_BASE_URL
        self.document_url = Config.CH_DOCUMENT_URL
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.auth = (self.api_key, '')
        self.session.headers.update({
            'User-Agent': 'SignalWatch/1.0'
        })
        
        # Ensure cache directory exists
        Config.ensure_directories()
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Make an API request with rate limiting and retries
        
        Args:
            url: Full URL to request
            method: HTTP method
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                # Acquire rate limit permission
                self.rate_limiter.acquire()
                
                # Make request
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', Config.RETRY_DELAY))
                    time.sleep(retry_after)
                    continue
                
                # Raise for other errors
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == Config.MAX_RETRIES - 1:
                    raise
                time.sleep(Config.RETRY_DELAY * (attempt + 1))
        
        raise Exception(f"Failed to request {url} after {Config.MAX_RETRIES} attempts")
    
    def get_company_profile(self, company_number: str) -> Dict[str, Any]:
        """
        Get company profile including current and previous names
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Company profile data
        """
        # Check cache first
        cache_file = Config.CACHE_DIR / f"profile_{company_number}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Fetch from API
        url = f"{self.base_url}/company/{company_number}"
        response = self._make_request(url)
        data = response.json()
        
        # Cache result
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return data
    
    def get_filing_history(self, company_number: str, 
                          category: Optional[str] = None,
                          items_per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get filing history for a company
        
        Args:
            company_number: Companies House company number
            category: Filter by category (e.g., 'incorporation', 'accounts')
            items_per_page: Results per page
            
        Returns:
            List of filing items
        """
        all_items = []
        start_index = 0
        
        while True:
            url = f"{self.base_url}/company/{company_number}/filing-history"
            params = {
                'items_per_page': items_per_page,
                'start_index': start_index
            }
            if category:
                params['category'] = category
            
            response = self._make_request(url, params=params)
            data = response.json()
            
            items = data.get('items', [])
            all_items.extend(items)
            
            # Check if there are more pages
            total = data.get('total_count', 0)
            if start_index + len(items) >= total:
                break
            
            start_index += items_per_page
        
        return all_items
    
    def get_document_metadata(self, company_number: str, 
                             transaction_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific document
        
        Args:
            company_number: Companies House company number
            transaction_id: Filing transaction ID
            
        Returns:
            Document metadata
        """
        url = f"{self.base_url}/company/{company_number}/filing-history/{transaction_id}"
        response = self._make_request(url)
        return response.json()
    
    def download_document(self, document_id: str, 
                         output_path: Optional[Path] = None,
                         company_number: Optional[str] = None) -> Path:
        """
        Download a document PDF
        
        Args:
            document_id: Document ID from filing history
            output_path: Where to save the PDF (auto-generated if not provided)
            company_number: Company number to organize PDFs in folders
            
        Returns:
            Path to downloaded PDF
        """
        if output_path is None:
            if company_number:
                # Save in company-specific folder
                company_dir = Config.DATA_DIR / company_number
                company_dir.mkdir(parents=True, exist_ok=True)
                output_path = company_dir / f"{document_id}.pdf"
            else:
                output_path = Config.DATA_DIR / f"{document_id}.pdf"
        
        # Check if already downloaded
        if output_path.exists():
            return output_path
        
        url = f"{self.document_url}/document/{document_id}/content"
        response = self._make_request(url)
        
        # Save PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return output_path
    
    def get_officers(self, company_number: str, 
                    items_per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get current and resigned officers (directors) for a company
        
        Args:
            company_number: Companies House company number
            items_per_page: Results per page
            
        Returns:
            List of officers
        """
        all_officers = []
        start_index = 0
        
        while True:
            url = f"{self.base_url}/company/{company_number}/officers"
            params = {
                'items_per_page': items_per_page,
                'start_index': start_index
            }
            
            response = self._make_request(url)
            data = response.json()
            
            items = data.get('items', [])
            all_officers.extend(items)
            
            # Check if there are more pages
            total = data.get('total_results', 0)
            if start_index + len(items) >= total:
                break
            
            start_index += items_per_page
        
        return all_officers
    
    def search_companies(self, query: str = None,
                        company_status: str = None,
                        company_type: str = None,
                        items_per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Search for companies with filters
        
        Args:
            query: Search query (company name or number)
            company_status: Filter by status (active, dissolved, etc.)
            company_status: Filter by company type
            items_per_page: Results per page
            
        Returns:
            List of companies
        """
        all_results = []
        start_index = 0
        
        while len(all_results) < 1000:  # Limit to prevent infinite loops
            url = f"{self.base_url}/search/companies"
            params = {
                'items_per_page': items_per_page,
                'start_index': start_index
            }
            
            if query:
                params['q'] = query
            if company_status:
                params['company_status'] = company_status
            if company_type:
                params['company_type'] = company_type
            
            try:
                response = self._make_request(url)
                data = response.json()
                
                items = data.get('items', [])
                if not items:
                    break
                    
                all_results.extend(items)
                
                # Check if there are more pages
                total = data.get('total_results', 0)
                if start_index + len(items) >= total or total == 0:
                    break
                
                start_index += items_per_page
            except Exception as e:
                print(f"Error searching companies: {e}")
                break
        
        return all_results
    
    def search_officers(self, officer_name: str, 
                       items_per_page: int = 50) -> List[Dict[str, Any]]:
        """
        Search for an officer across all companies
        
        Args:
            officer_name: Name of officer to search for
            items_per_page: Results per page
            
        Returns:
            List of officer appointments
        """
        all_results = []
        start_index = 0
        
        while True:
            url = f"{self.base_url}/search/officers"
            params = {
                'q': officer_name,
                'items_per_page': items_per_page,
                'start_index': start_index
            }
            
            response = self._make_request(url, params=params)
            data = response.json()
            
            items = data.get('items', [])
            all_results.extend(items)
            
            # Check if there are more pages
            total = data.get('total_results', 0)
            if start_index + len(items) >= total or start_index >= 200:  # API limit
                break
            
            start_index += items_per_page
        
        return all_results
    
    def get_officer_appointments(self, officer_id: str) -> List[Dict[str, Any]]:
        """
        Get all appointments for a specific officer
        
        Args:
            officer_id: Officer ID from search results
            
        Returns:
            List of appointments
        """
        url = f"{self.base_url}/officers/{officer_id}/appointments"
        response = self._make_request(url)
        data = response.json()
        return data.get('items', [])
    
    def get_company_search(self, query: str, 
                          items_per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Search for companies by name or number
        
        Args:
            query: Search query
            items_per_page: Results per page
            
        Returns:
            List of matching companies
        """
        url = f"{self.base_url}/search/companies"
        params = {
            'q': query,
            'items_per_page': items_per_page
        }
        
        response = self._make_request(url, params=params)
        data = response.json()
        return data.get('items', [])
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status
        
        Returns:
            Dictionary with remaining requests and reset time
        """
        return {
            'remaining_requests': self.rate_limiter.get_remaining_requests(),
            'reset_time_seconds': self.rate_limiter.get_reset_time(),
            'max_requests': self.rate_limiter.max_requests,
            'period_seconds': self.rate_limiter.period
        }
