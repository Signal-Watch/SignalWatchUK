"""
Network Scanner - Discovers company networks through shared directors
"""
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict
from core.api_client import CompaniesHouseClient


class NetworkScanner:
    """Scan and map company networks through director connections"""
    
    def __init__(self, api_client: Optional[CompaniesHouseClient] = None):
        """
        Initialize network scanner
        
        Args:
            api_client: Companies House API client (creates new if not provided)
        """
        self.api_client = api_client or CompaniesHouseClient()
        self.scanned_companies = set()
        self.scanned_officers = set()
    
    def scan_network(self,
                    seed_companies: List[str],
                    max_depth: int = 2,
                    max_companies: int = 100,
                    active_only: bool = True) -> Dict[str, Any]:
        """
        Scan director network starting from seed companies
        
        Args:
            seed_companies: List of company numbers to start from
            max_depth: How many levels deep to scan
            max_companies: Maximum companies to scan
            active_only: Only include active directors/companies
            
        Returns:
            Network data with companies, directors, and connections
        """
        network = {
            'seed_companies': seed_companies,
            'max_depth': max_depth,
            'companies': {},
            'directors': {},
            'connections': [],
            'statistics': {
                'total_companies': 0,
                'total_directors': 0,
                'total_connections': 0,
                'depth_reached': 0
            }
        }
        
        # Reset tracking
        self.scanned_companies = set()
        self.scanned_officers = set()
        
        # Start scanning from seed companies
        companies_to_scan = [(cnum, 0) for cnum in seed_companies]
        
        while companies_to_scan and len(self.scanned_companies) < max_companies:
            company_number, depth = companies_to_scan.pop(0)
            
            # Skip if already scanned or max depth reached
            if company_number in self.scanned_companies or depth > max_depth:
                continue
            
            print(f"Scanning company {company_number} at depth {depth}...")
            
            try:
                # Get company profile
                profile = self.api_client.get_company_profile(company_number)
                
                # Skip if inactive and active_only is True
                if active_only and profile.get('company_status') != 'active':
                    continue
                
                # Get officers
                officers = self.api_client.get_officers(company_number)
                
                # Filter active officers if requested
                if active_only:
                    officers = [
                        o for o in officers 
                        if not o.get('resigned_on')
                    ]
                
                # Store company data
                network['companies'][company_number] = {
                    'company_number': company_number,
                    'company_name': profile.get('company_name'),
                    'company_status': profile.get('company_status'),
                    'company_type': profile.get('type'),
                    'incorporation_date': profile.get('date_of_creation'),
                    'depth': depth,
                    'officer_count': len(officers)
                }
                
                self.scanned_companies.add(company_number)
                network['statistics']['depth_reached'] = max(
                    network['statistics']['depth_reached'], depth
                )
                
                # Process each officer
                for officer in officers:
                    officer_name = officer.get('name', '')
                    officer_role = officer.get('officer_role', '')
                    officer_id = f"{officer_name}_{officer.get('appointed_on', '')}"
                    
                    # Store director data
                    if officer_id not in network['directors']:
                        network['directors'][officer_id] = {
                            'name': officer_name,
                            'appointments': [],
                            'company_count': 0
                        }
                    
                    # Record appointment with DOB
                    appointment = {
                        'company_number': company_number,
                        'company_name': profile.get('company_name'),
                        'role': officer_role,
                        'appointed_on': officer.get('appointed_on'),
                        'resigned_on': officer.get('resigned_on')
                    }
                    
                    # Add date of birth if available
                    if 'date_of_birth' in officer:
                        appointment['date_of_birth'] = officer['date_of_birth']
                    
                    network['directors'][officer_id]['appointments'].append(appointment)
                    
                    network['directors'][officer_id]['company_count'] = len(
                        network['directors'][officer_id]['appointments']
                    )
                    
                    # Record connection
                    network['connections'].append({
                        'company_number': company_number,
                        'company_name': profile.get('company_name'),
                        'director_id': officer_id,
                        'director_name': officer_name,
                        'role': officer_role,
                        'depth': depth
                    })
                    
                    # If not at max depth, find other companies for this director
                    if depth < max_depth and officer_id not in self.scanned_officers:
                        try:
                            # Skip corporate officers (companies as officers) - they don't have searchable records
                            if any(keyword in officer_name.upper() for keyword in ['LIMITED', 'LTD', 'PLC', 'LLP', 'COMPANY', 'CORPORATE']):
                                self.scanned_officers.add(officer_id)
                                continue
                            
                            # Search for this officer
                            officer_results = self.api_client.search_officers(officer_name)
                            
                            if officer_results:
                                # Get the BEST match only (exact name match if possible)
                                best_match = None
                                for officer_match in officer_results[:5]:  # Check top 5
                                    match_name = officer_match.get('title', '')
                                    # Exact match preferred
                                    if match_name.upper() == officer_name.upper():
                                        best_match = officer_match
                                        break
                                
                                # If no exact match, use first result
                                if not best_match and officer_results:
                                    best_match = officer_results[0]
                                
                                if best_match:
                                    match_id = best_match.get('links', {}).get('self', '')
                                    if match_id:
                                        # Extract officer ID from URL
                                        officer_api_id = match_id.split('/')[-2]
                                        
                                        try:
                                            # Get all appointments
                                            appointments = self.api_client.get_officer_appointments(
                                                officer_api_id
                                            )
                                            
                                            # Filter appointments - only include if this officer is actually in that company
                                            for appt in appointments:
                                                appt_company = appt.get('appointed_to', {}).get('company_number')
                                                officer_status = appt.get('resigned_on')
                                                
                                                # Skip if company already scanned
                                                if not appt_company or appt_company in self.scanned_companies:
                                                    continue
                                                
                                                # Skip resigned directors if active_only
                                                if active_only and officer_status:
                                                    continue
                                                
                                                # Skip if company is inactive and active_only
                                                company_status = appt.get('appointed_to', {}).get('company_status')
                                                if active_only and company_status != 'active':
                                                    continue
                                                
                                                companies_to_scan.append((appt_company, depth + 1))
                                        except Exception as appt_error:
                                            # Skip 404 errors for dissolved/inactive officers
                                            if '404' not in str(appt_error):
                                                print(f"Error getting appointments for officer {officer_name}: {appt_error}")
                            
                            self.scanned_officers.add(officer_id)
                            
                        except Exception as e:
                            # Don't print 404 errors - they're expected for corporate/dissolved officers
                            if '404' not in str(e):
                                print(f"Error searching for officer {officer_name}: {e}")
                
            except Exception as e:
                print(f"Error scanning company {company_number}: {e}")
        
        # Update statistics
        network['statistics']['total_companies'] = len(network['companies'])
        network['statistics']['total_directors'] = len(network['directors'])
        network['statistics']['total_connections'] = len(network['connections'])
        
        return network
    
    def find_shared_directors(self, network: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find directors who are connected to multiple companies
        
        Args:
            network: Network data from scan_network
            
        Returns:
            List of directors with multiple companies
        """
        shared = []
        
        for director_id, director_data in network['directors'].items():
            if director_data['company_count'] > 1:
                shared.append({
                    'director_id': director_id,
                    'director_name': director_data['name'],
                    'company_count': director_data['company_count'],
                    'companies': [
                        {
                            'company_number': appt['company_number'],
                            'company_name': appt['company_name'],
                            'role': appt['role']
                        }
                        for appt in director_data['appointments']
                    ]
                })
        
        # Sort by company count (most connected first)
        shared.sort(key=lambda x: x['company_count'], reverse=True)
        
        return shared
    
    def find_company_clusters(self, network: Dict[str, Any]) -> List[List[str]]:
        """
        Find clusters of companies connected through shared directors
        
        Args:
            network: Network data from scan_network
            
        Returns:
            List of company clusters
        """
        # Build adjacency list
        graph = defaultdict(set)
        
        for connection in network['connections']:
            company = connection['company_number']
            director = connection['director_id']
            
            # Find all companies with this director
            related_companies = [
                c['company_number'] 
                for c in network['connections']
                if c['director_id'] == director
            ]
            
            for related in related_companies:
                if related != company:
                    graph[company].add(related)
        
        # Find connected components (clusters)
        visited = set()
        clusters = []
        
        def dfs(node, cluster):
            visited.add(node)
            cluster.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, cluster)
        
        for company in network['companies']:
            if company not in visited:
                cluster = []
                dfs(company, cluster)
                if len(cluster) > 1:  # Only include clusters with multiple companies
                    clusters.append(cluster)
        
        # Sort by cluster size
        clusters.sort(key=len, reverse=True)
        
        return clusters
    
    def generate_network_report(self, network: Dict[str, Any]) -> str:
        """
        Generate human-readable network report
        
        Args:
            network: Network data from scan_network
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("DIRECTOR NETWORK ANALYSIS")
        report.append("=" * 80)
        report.append(f"Seed Companies: {', '.join(network['seed_companies'])}")
        report.append(f"Max Depth: {network['max_depth']}")
        report.append("")
        
        stats = network['statistics']
        report.append("STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Companies: {stats['total_companies']}")
        report.append(f"Total Directors: {stats['total_directors']}")
        report.append(f"Total Connections: {stats['total_connections']}")
        report.append(f"Depth Reached: {stats['depth_reached']}")
        report.append("")
        
        # Shared directors
        shared = self.find_shared_directors(network)
        if shared:
            report.append("TOP SHARED DIRECTORS")
            report.append("-" * 80)
            for director in shared[:10]:  # Top 10
                report.append(f"\n{director['director_name']}")
                report.append(f"  Companies: {director['company_count']}")
                for company in director['companies'][:5]:  # First 5
                    report.append(f"    - {company['company_name']} ({company['company_number']}) as {company['role']}")
        
        report.append("")
        
        # Company clusters
        clusters = self.find_company_clusters(network)
        if clusters:
            report.append("COMPANY CLUSTERS")
            report.append("-" * 80)
            for i, cluster in enumerate(clusters[:5], 1):  # Top 5 clusters
                report.append(f"\nCluster {i} ({len(cluster)} companies):")
                for company_num in cluster[:10]:  # First 10 in cluster
                    company_data = network['companies'].get(company_num, {})
                    report.append(f"  - {company_data.get('company_name')} ({company_num})")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
