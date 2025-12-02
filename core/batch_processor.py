"""
Batch Processor - Scalable processing with checkpoints and resume capability
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from config import Config
from core.api_client import CompaniesHouseClient
from core.pdf_processor import PDFProcessor
from core.mismatch_detector import MismatchDetector
from core.network_scanner import NetworkScanner
from parsers import DocumentParser


class BatchProcessor:
    """Process multiple companies with checkpoint/resume capability"""
    
    def __init__(self, api_client: Optional[CompaniesHouseClient] = None):
        """
        Initialize batch processor
        
        Args:
            api_client: Companies House API client
        """
        self.api_client = api_client or CompaniesHouseClient()
        self.pdf_processor = PDFProcessor()
        self.document_parser = DocumentParser()
        self.mismatch_detector = MismatchDetector()
        self.network_scanner = NetworkScanner(self.api_client)
        
        Config.ensure_directories()
    
    def process_companies(self,
                         company_numbers: List[str],
                         scan_network: bool = False,
                         network_depth: int = 1,
                         active_only: bool = True,
                         use_ai: bool = False,
                         checkpoint_file: Optional[Path] = None,
                         progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Process multiple companies with mismatch detection
        
        Args:
            company_numbers: List of company numbers to process
            scan_network: Whether to scan director networks
            network_depth: Depth for network scanning
            checkpoint_file: Path to save checkpoints
            progress_callback: Function to call with progress updates
            
        Returns:
            Processing results
        """
        if checkpoint_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            checkpoint_file = Config.DATA_DIR / f'checkpoint_{timestamp}.json'
        
        # Load checkpoint if exists
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                results = json.load(f)
                processed = set(results.get('processed_companies', []))
        else:
            results = {
                'started_at': datetime.now().isoformat(),
                'company_numbers': company_numbers,
                'scan_network': scan_network,
                'processed_companies': [],
                'results': [],
                'network': None,
                'errors': []
            }
            processed = set()
        
        # Process each company
        total = len(company_numbers)
        for idx, company_number in enumerate(company_numbers):
            if company_number in processed:
                continue
            
            if progress_callback:
                progress_callback({
                    'current': idx + 1,
                    'total': total,
                    'company_number': company_number,
                    'status': 'processing'
                })
            
            try:
                # Process company
                company_result = self._process_single_company(company_number, use_ai=use_ai)
                results['results'].append(company_result)
                results['processed_companies'].append(company_number)
                
                # Save checkpoint
                if (idx + 1) % Config.CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(checkpoint_file, results)
                
            except Exception as e:
                error_info = {
                    'company_number': company_number,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results['errors'].append(error_info)
                print(f"Error processing {company_number}: {e}")
        
        # Network scanning
        if scan_network:
            if progress_callback:
                progress_callback({
                    'status': 'scanning_network',
                    'message': 'Scanning director networks...'
                })
            
            try:
                network = self.network_scanner.scan_network(
                    seed_companies=company_numbers,
                    max_depth=network_depth,
                    active_only=active_only
                )
                results['network'] = network
            except Exception as e:
                results['errors'].append({
                    'type': 'network_scan_error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Finalize results
        results['completed_at'] = datetime.now().isoformat()
        results['total_processed'] = len(results['processed_companies'])
        results['total_errors'] = len(results['errors'])
        
        # Save final results
        self._save_checkpoint(checkpoint_file, results)
        
        return results
    
    def _process_single_company(self, company_number: str, use_ai: bool = False) -> Dict[str, Any]:
        """
        Process a single company
        
        Args:
            company_number: Company number to process
            use_ai: Whether to use AI extraction (fast but costs)
            
        Returns:
            Processing result
        """
        result = {
            'company_number': company_number,
            'processed_at': datetime.now().isoformat()
        }
        
        # Get company profile
        profile = self.api_client.get_company_profile(company_number)
        result['company_name'] = profile.get('company_name')
        result['company_status'] = profile.get('company_status')
        
        # Get filing history
        filing_history = self.api_client.get_filing_history(company_number)
        
        # Filter relevant documents
        relevant_filings = self._filter_relevant_filings(filing_history)
        result['total_filings'] = len(filing_history)
        result['relevant_filings'] = len(relevant_filings)
        
        # Download and parse documents
        parsed_documents = []
        for filing in relevant_filings[:10]:  # Limit to first 10 documents
            try:
                # Get document metadata
                links = filing.get('links', {})
                document_id = links.get('document_metadata', '').split('/')[-1]
                
                if document_id:
                    # Download PDF to company-specific folder
                    pdf_path = self.api_client.download_document(document_id, company_number=company_number)
                    
                    # Parse document - OCR only by default (no AI costs)
                    # Set use_ai=True only if you want to use AI extraction
                    parsed = self.document_parser.parse_document(
                        pdf_path, 
                        use_ocr=not use_ai,  # Skip OCR if AI mode enabled
                        use_ai=use_ai,  # Use AI based on user toggle
                        prefer_ocr=not use_ai  # Prefer OCR only if AI disabled
                    )
                    parsed_documents.append(parsed)
                    
            except Exception as e:
                print(f"Error processing filing {filing.get('transaction_id')}: {e}")
        
        result['parsed_documents'] = len(parsed_documents)
        
        # Detect mismatches
        mismatch_results = self.mismatch_detector.detect_mismatches(
            company_profile=profile,
            filing_data={'items': filing_history},
            parsed_documents=parsed_documents
        )
        
        result['mismatches'] = mismatch_results
        
        return result
    
    def _filter_relevant_filings(self, filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter filings to only relevant document types
        
        Args:
            filings: All filing history items
            
        Returns:
            Filtered list of relevant filings
        """
        relevant_categories = {
            'incorporation',
            'change-of-name',
            'reregistration',
            'resolution'
        }
        
        relevant = []
        for filing in filings:
            category = filing.get('category', '')
            description = filing.get('description', '').lower()
            
            # Include if category matches or description mentions name change
            if (category in relevant_categories or 
                'change of name' in description or
                'changed its name' in description):
                relevant.append(filing)
        
        return relevant
    
    def _save_checkpoint(self, checkpoint_file: Path, data: Dict[str, Any]):
        """
        Save checkpoint data
        
        Args:
            checkpoint_file: Path to checkpoint file
            data: Data to save
        """
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def resume_from_checkpoint(self, 
                              checkpoint_file: Path,
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Resume processing from a checkpoint
        
        Args:
            checkpoint_file: Path to checkpoint file
            progress_callback: Progress callback function
            
        Returns:
            Processing results
        """
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")
        
        # Load checkpoint
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        
        company_numbers = checkpoint.get('company_numbers', [])
        scan_network = checkpoint.get('scan_network', False)
        
        # Continue processing
        return self.process_companies(
            company_numbers=company_numbers,
            scan_network=scan_network,
            checkpoint_file=checkpoint_file,
            progress_callback=progress_callback
        )
    
    def get_processing_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary statistics from processing results
        
        Args:
            results: Processing results
            
        Returns:
            Summary statistics
        """
        summary = {
            'total_companies': len(results.get('company_numbers', [])),
            'processed_companies': results.get('total_processed', 0),
            'total_errors': results.get('total_errors', 0),
            'total_mismatches': 0,
            'companies_with_mismatches': 0,
            'mismatch_types': {}
        }
        
        # Analyze mismatches
        for company_result in results.get('results', []):
            mismatch_data = company_result.get('mismatches', {})
            mismatches = mismatch_data.get('mismatches', [])
            
            if mismatches:
                summary['companies_with_mismatches'] += 1
                summary['total_mismatches'] += len(mismatches)
                
                # Count by type
                for mismatch in mismatches:
                    mtype = mismatch.get('type', 'unknown')
                    summary['mismatch_types'][mtype] = summary['mismatch_types'].get(mtype, 0) + 1
        
        # Network statistics
        if results.get('network'):
            network = results['network']
            summary['network'] = {
                'total_companies': network['statistics']['total_companies'],
                'total_directors': network['statistics']['total_directors'],
                'total_connections': network['statistics']['total_connections']
            }
        
        return summary
