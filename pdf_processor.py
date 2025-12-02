"""
PDF Processor - Downloads and extracts text from Companies House documents
"""
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from config import Config


class PDFProcessor:
    """Handles PDF download, text extraction, and OCR"""
    
    def __init__(self):
        """Initialize PDF processor"""
        Config.ensure_directories()
        
        # Try to detect Tesseract on Windows
        if os.name == 'nt':
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                os.path.join(os.getenv('LOCALAPPDATA', ''), 'Programs', 'Tesseract-OCR', 'tesseract.exe')
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
    
    def extract_text_from_pdf(self, pdf_path: Path, use_ocr: bool = True) -> str:
        """
        Extract text from PDF using PyPDF2 and fallback to OCR if needed
        
        Args:
            pdf_path: Path to PDF file
            use_ocr: Whether to use OCR if text extraction fails
            
        Returns:
            Extracted text
        """
        text = ""
        
        try:
            # Try native text extraction first
            text = self._extract_native_text(pdf_path)
            
            # If little to no text extracted and OCR enabled, try OCR
            if use_ocr and len(text.strip()) < 100:
                ocr_text = self._extract_with_ocr(pdf_path)
                if len(ocr_text) > len(text):
                    text = ocr_text
                    
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            if use_ocr:
                try:
                    text = self._extract_with_ocr(pdf_path)
                except Exception as ocr_e:
                    print(f"OCR also failed: {ocr_e}")
        
        return text
    
    def _extract_native_text(self, pdf_path: Path) -> str:
        """
        Extract text using PyPDF2 (for native text PDFs)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        text = ""
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text
    
    def _extract_with_ocr(self, pdf_path: Path) -> str:
        """
        Extract text using OCR (for scanned PDFs)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        text = ""
        
        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            dpi=Config.PDF_DPI,
            fmt='jpeg'
        )
        
        # OCR each page
        for i, image in enumerate(images):
            try:
                page_text = pytesseract.image_to_string(
                    image,
                    lang=Config.OCR_LANGUAGE
                )
                text += f"\n--- Page {i+1} ---\n{page_text}\n"
            except Exception as e:
                print(f"Error OCR'ing page {i+1}: {e}")
        
        return text
    
    def extract_with_ai(self, pdf_path: Path, api_key: Optional[str] = None) -> str:
        """
        Extract text using AI API (XAI Grok or OpenAI - more accurate for complex layouts)
        
        Args:
            pdf_path: Path to PDF file
            api_key: API key (uses config if not provided)
            
        Returns:
            Extracted text
        """
        provider = Config.AI_PROVIDER
        
        if provider == 'xai':
            return self._extract_with_xai(pdf_path, api_key)
        else:
            return self._extract_with_openai(pdf_path, api_key)
    
    def _extract_with_xai(self, pdf_path: Path, api_key: Optional[str] = None) -> str:
        """Extract text using XAI (Grok) - faster and cheaper"""
        try:
            import requests
            import base64
            
            api_key = api_key or Config.XAI_API_KEY
            if not api_key:
                raise ValueError("XAI API key required for AI extraction")
            
            # Convert first few pages to images
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=3)
            
            all_text = []
            
            for idx, image in enumerate(images):
                # Save temp image
                temp_image = Config.CACHE_DIR / f"temp_{pdf_path.stem}_p{idx}.jpg"
                image.save(temp_image, 'JPEG')
                
                # Encode image
                with open(temp_image, 'rb') as f:
                    image_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Call XAI API
                response = requests.post(
                    f"{Config.XAI_BASE_URL}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    },
                    json={
                        "model": Config.XAI_MODEL,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all text from this Companies House document. Focus on: company names, dates, registration numbers, and director information. Return only the extracted text, no explanations."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }],
                        "temperature": 0.3,
                        "max_tokens": 1500
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    page_text = result['choices'][0]['message']['content']
                    all_text.append(f"--- Page {idx+1} ---\n{page_text}")
                else:
                    print(f"⚠️  XAI API error on page {idx+1}: {response.status_code}")
                    print(f"   Response: {response.text}")
                
                # Clean up temp file
                temp_image.unlink()
            
            return "\n\n".join(all_text)
            
        except Exception as e:
            print(f"❌ XAI extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _extract_with_openai(self, pdf_path: Path, api_key: Optional[str] = None) -> str:
        """Extract text using OpenAI (alternative option)"""
        try:
            import openai
            
            openai.api_key = api_key or Config.OPENAI_API_KEY
            if not openai.api_key:
                raise ValueError("OpenAI API key required for AI extraction")
            
            # Convert first page to image for vision API
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
            
            # Save temp image
            temp_image = Config.CACHE_DIR / f"temp_{pdf_path.stem}.jpg"
            images[0].save(temp_image, 'JPEG')
            
            # Use vision API to extract text
            with open(temp_image, 'rb') as image_file:
                response = openai.ChatCompletion.create(
                    model="gpt-4-vision-preview",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this document, preserving structure and formatting. Focus on company names, dates, and registration details."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{self._encode_image(temp_image)}"
                                }
                            }
                        ]
                    }],
                    max_tokens=2000
                )
            
            # Clean up temp file
            temp_image.unlink()
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI extraction failed: {e}")
            return ""
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64"""
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract PDF metadata
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Basic info
                metadata['num_pages'] = len(pdf_reader.pages)
                
                # Document metadata
                if pdf_reader.metadata:
                    metadata['title'] = pdf_reader.metadata.get('/Title', '')
                    metadata['author'] = pdf_reader.metadata.get('/Author', '')
                    metadata['subject'] = pdf_reader.metadata.get('/Subject', '')
                    metadata['creator'] = pdf_reader.metadata.get('/Creator', '')
                    metadata['producer'] = pdf_reader.metadata.get('/Producer', '')
                    
                    # Try to get dates
                    creation_date = pdf_reader.metadata.get('/CreationDate', '')
                    if creation_date:
                        metadata['creation_date'] = self._parse_pdf_date(creation_date)
                    
                    mod_date = pdf_reader.metadata.get('/ModDate', '')
                    if mod_date:
                        metadata['modification_date'] = self._parse_pdf_date(mod_date)
                
        except Exception as e:
            print(f"Error extracting metadata from {pdf_path}: {e}")
        
        return metadata
    
    def _parse_pdf_date(self, date_string: str) -> Optional[str]:
        """
        Parse PDF date format (D:YYYYMMDDHHmmSS)
        
        Args:
            date_string: PDF date string
            
        Returns:
            ISO format date string
        """
        try:
            # PDF date format: D:YYYYMMDDHHmmSS+HH'mm'
            match = re.search(r'D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', date_string)
            if match:
                year, month, day, hour, minute, second = match.groups()
                return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        except Exception:
            pass
        return None
    
    def analyze_document_type(self, text: str) -> str:
        """
        Determine document type from text content
        
        Args:
            text: Extracted text
            
        Returns:
            Document type (incorporation, name_change, accounts, etc.)
        """
        text_lower = text.lower()
        
        if 'certificate of incorporation' in text_lower:
            return 'incorporation'
        elif 'change of name' in text_lower or 'changed its name' in text_lower:
            return 'name_change'
        elif 'annual accounts' in text_lower or 'financial statements' in text_lower:
            return 'accounts'
        elif 'confirmation statement' in text_lower or 'annual return' in text_lower:
            return 'confirmation_statement'
        elif 're-registration' in text_lower:
            return 're_registration'
        elif 'appointment' in text_lower and 'director' in text_lower:
            return 'director_appointment'
        elif 'resignation' in text_lower and 'director' in text_lower:
            return 'director_resignation'
        elif 'registered office' in text_lower:
            return 'address_change'
        else:
            return 'unknown'
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text (remove extra whitespace, fix common OCR errors)
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Fix common OCR mistakes
        replacements = {
            r'\b0\b': 'O',  # Zero to O in company names
            r'l(?=[A-Z])': 'I',  # lowercase l to I before capitals
            r'(?<=[A-Z])l(?=[A-Z])': 'I',  # lowercase l to I between capitals
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text.strip()
