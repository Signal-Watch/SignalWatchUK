"""
CSV Exporter - Export results to CSV format
"""
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import Config


class CSVExporter:
    """Export processing results to CSV files"""
    
    def __init__(self):
        """Initialize CSV exporter"""
        Config.ensure_directories()
    
    def export_mismatches(self, 
                         results: Dict[str, Any],
                         output_file: Optional[Path] = None) -> Path:
        """
        Export mismatch results to CSV
        
        Args:
            results: Processing results from BatchProcessor
            output_file: Output file path (auto-generated if not provided)
            
        Returns:
            Path to created CSV file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Config.EXPORTS_DIR / f'mismatches_{timestamp}.csv'
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare rows
        rows = []
        
        for company_result in results.get('results', []):
            company_number = company_result.get('company_number')
            company_name = company_result.get('company_name')
            mismatch_data = company_result.get('mismatches', {})
            
            mismatches = mismatch_data.get('mismatches', [])
            
            if mismatches:
                for mismatch in mismatches:
                    row = {
                        'Company Number': company_number,
                        'Company Name': company_name,
                        'Mismatch Type': mismatch.get('type', ''),
                        'Severity': mismatch.get('severity', ''),
                        'Document': mismatch.get('document', ''),
                        'Expected': self._format_expected(mismatch),
                        'Found': self._format_found(mismatch),
                        'Confidence': mismatch.get('confidence', ''),
                        'Message': mismatch.get('message', '')
                    }
                    rows.append(row)
            else:
                # Include companies with no mismatches
                rows.append({
                    'Company Number': company_number,
                    'Company Name': company_name,
                    'Mismatch Type': 'None',
                    'Severity': 'N/A',
                    'Document': '',
                    'Expected': '',
                    'Found': '',
                    'Confidence': '',
                    'Message': 'No mismatches detected'
                })
        
        # Write CSV
        if rows:
            fieldnames = rows[0].keys()
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return output_file
    
    def export_network(self,
                      network: Dict[str, Any],
                      output_file: Optional[Path] = None) -> Path:
        """
        Export network connections to CSV
        
        Args:
            network: Network data from NetworkScanner
            output_file: Output file path
            
        Returns:
            Path to created CSV file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Config.EXPORTS_DIR / f'network_{timestamp}.csv'
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare rows
        rows = []
        
        # Get directors info for DOB lookup
        directors = network.get('directors', {})
        
        for connection in network.get('connections', []):
            director_id = connection.get('director_id')
            director_info = directors.get(director_id, {})
            
            # Try to get DOB from appointments
            dob = 'N/A'
            appointments = director_info.get('appointments', [])
            if appointments:
                first_appt = appointments[0]
                if 'date_of_birth' in first_appt:
                    dob_data = first_appt['date_of_birth']
                    if isinstance(dob_data, dict):
                        dob = f"{dob_data.get('month', '?')}/{dob_data.get('year', '?')}"
                    else:
                        dob = str(dob_data) if dob_data else 'N/A'
            
            row = {
                'Company Number': connection.get('company_number'),
                'Company Name': connection.get('company_name'),
                'Director Name': connection.get('director_name'),
                'Date of Birth': dob,
                'Role': connection.get('role'),
                'Depth': connection.get('depth')
            }
            rows.append(row)
        
        # Write CSV
        if rows:
            fieldnames = rows[0].keys()
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return output_file
    
    def export_summary(self,
                      results: Dict[str, Any],
                      output_file: Optional[Path] = None) -> Path:
        """
        Export summary statistics to CSV
        
        Args:
            results: Processing results
            output_file: Output file path
            
        Returns:
            Path to created CSV file
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Config.EXPORTS_DIR / f'summary_{timestamp}.csv'
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare summary rows
        rows = []
        
        for company_result in results.get('results', []):
            mismatch_data = company_result.get('mismatches', {})
            summary = mismatch_data.get('summary', {})
            
            row = {
                'Company Number': company_result.get('company_number'),
                'Company Name': company_result.get('company_name'),
                'Company Status': company_result.get('company_status'),
                'Total Filings': company_result.get('total_filings', 0),
                'Relevant Filings': company_result.get('relevant_filings', 0),
                'Parsed Documents': company_result.get('parsed_documents', 0),
                'Total Mismatches': summary.get('total_mismatches', 0),
                'Name Mismatches': summary.get('name_mismatches', 0),
                'Date Mismatches': summary.get('date_mismatches', 0),
                'Missing Filings': summary.get('missing_filings', 0),
                'Extra Names': summary.get('extra_names', 0)
            }
            rows.append(row)
        
        # Write CSV
        if rows:
            fieldnames = rows[0].keys()
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return output_file
    
    def _format_expected(self, mismatch: Dict[str, Any]) -> str:
        """Format expected value for CSV"""
        if 'expected_names' in mismatch:
            return ', '.join(mismatch['expected_names'])
        elif 'expected_date' in mismatch:
            return mismatch['expected_date']
        return ''
    
    def _format_found(self, mismatch: Dict[str, Any]) -> str:
        """Format found value for CSV"""
        if 'found_name' in mismatch:
            return mismatch['found_name']
        elif 'found_date' in mismatch:
            return mismatch['found_date']
        return ''


from typing import Optional
