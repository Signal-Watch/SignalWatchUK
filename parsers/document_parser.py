"""
Document Parser - Combines PDF processing with name and date extraction
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.pdf_processor import PDFProcessor
from .name_parser import NameParser
from .date_parser import DateParser


class DocumentParser:
    """High-level document parsing that combines all extraction capabilities"""
    
    def __init__(self):
        """Initialize document parser"""
        self.pdf_processor = PDFProcessor()
        self.name_parser = NameParser()
        self.date_parser = DateParser()
    
    def parse_document(self, pdf_path: Path, 
                      use_ocr: bool = True,
                      use_ai: bool = False,
                      prefer_ocr: bool = True) -> Dict[str, Any]:
        """
        Parse a Companies House document completely
        
        Args:
            pdf_path: Path to PDF file
            use_ocr: Whether to use OCR for scanned documents (FREE)
            use_ai: Whether to use AI for advanced extraction (COSTS TOKENS)
            prefer_ocr: Try OCR first to minimize AI costs
            
        Returns:
            Dictionary with all extracted information
        """
        result = {
            'file_path': str(pdf_path),
            'file_name': pdf_path.name,
            'parsed_at': datetime.now().isoformat(),
            'success': False,
            'error': None
        }
        
        try:
            # Extract text - Try OCR first to minimize AI costs
            text = ""
            
            if prefer_ocr and use_ocr:
                # Try free OCR first
                text = self.pdf_processor.extract_text_from_pdf(pdf_path, use_ocr=True)
            
            # Only use AI if OCR failed and AI is enabled
            if (not text or len(text.strip()) < 50) and use_ai:
                print(f"  💰 Using AI extraction (costs tokens) for {pdf_path.name}")
                text = self.pdf_processor.extract_with_ai(pdf_path)
            elif not text:
                # Fallback to basic extraction
                text = self.pdf_processor.extract_text_from_pdf(pdf_path, use_ocr=False)
            
            if not text:
                result['error'] = 'No text could be extracted from document'
                return result
            
            # Clean text
            cleaned_text = self.pdf_processor.clean_text(text)
            
            # Determine document type
            doc_type = self.pdf_processor.analyze_document_type(cleaned_text)
            
            # Extract metadata
            metadata = self.pdf_processor.extract_metadata(pdf_path)
            
            # Extract names
            names = self.name_parser.extract_names(cleaned_text)
            
            # Extract name changes if applicable
            name_changes = self.name_parser.extract_name_changes(cleaned_text)
            
            # Extract dates
            dates = self.date_parser.extract_dates(cleaned_text, doc_type)
            
            # Extract specific dates based on document type
            incorporation_date = None
            name_change_date = None
            
            if doc_type == 'incorporation':
                incorporation_date = self.date_parser.extract_incorporation_date(cleaned_text)
            elif doc_type == 'name_change':
                name_change_date = self.date_parser.extract_name_change_date(cleaned_text)
            
            # Compile results
            result.update({
                'success': True,
                'document_type': doc_type,
                'text_length': len(cleaned_text),
                'metadata': metadata,
                'names': names,
                'name_changes': name_changes,
                'dates': [d.isoformat() for d in dates],
                'incorporation_date': incorporation_date.isoformat() if incorporation_date else None,
                'name_change_date': name_change_date.isoformat() if name_change_date else None,
                'text_preview': cleaned_text[:500] if cleaned_text else None
            })
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def parse_batch(self, pdf_paths: List[Path], 
                   use_ocr: bool = True) -> List[Dict[str, Any]]:
        """
        Parse multiple documents
        
        Args:
            pdf_paths: List of paths to PDF files
            use_ocr: Whether to use OCR
            
        Returns:
            List of parsing results
        """
        results = []
        
        for pdf_path in pdf_paths:
            result = self.parse_document(pdf_path, use_ocr)
            results.append(result)
        
        return results
    
    def extract_for_mismatch_detection(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract only information needed for mismatch detection
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Simplified extraction result
        """
        result = self.parse_document(pdf_path)
        
        if not result['success']:
            return result
        
        # Return only mismatch-relevant data
        return {
            'file_name': result['file_name'],
            'document_type': result['document_type'],
            'names': result['names'],
            'name_changes': result['name_changes'],
            'dates': result['dates'],
            'incorporation_date': result['incorporation_date'],
            'name_change_date': result['name_change_date'],
            'success': True
        }
