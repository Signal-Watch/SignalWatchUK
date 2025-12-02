#!/usr/bin/env python3
"""
Test AI extraction directly
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.pdf_processor import PDFProcessor

def test_ai_extraction():
    pdf_file = Path("data/01002769/V8WwtKQFwH6q04Yzz-jkzNaRahDgEYt2gQfN6sEGWcc.pdf")
    
    print("\n🤖 Testing AI Extraction (Grok)\n")
    
    processor = PDFProcessor()
    
    try:
        text = processor.extract_with_ai(pdf_file)
        text_len = len(text.strip())
        
        print(f"✅ AI Extraction Successful!")
        print(f"   Extracted: {text_len} characters\n")
        print(f"   Sample:\n{text[:500]}\n")
        
    except Exception as e:
        print(f"❌ AI Extraction Failed!")
        print(f"   Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_ai_extraction()
