#!/usr/bin/env python3
"""
Deep Diagnostic: Check what's wrong with PDF extraction
"""
import sys
from pathlib import Path
import PyPDF2
from pdf2image import convert_from_path

sys.path.insert(0, str(Path(__file__).parent))

def diagnose_pdf():
    """Diagnose PDF extraction issues"""
    
    print("\n" + "="*70)
    print("🔬 DEEP PDF DIAGNOSTICS")
    print("="*70 + "\n")
    
    # Use the account PDF
    pdf_file = Path("data/01002769/.pdf")
    
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_file}")
        return
    
    print(f"📄 Analyzing: {pdf_file}")
    print(f"   Size: {pdf_file.stat().st_size} bytes\n")
    
    # Test 1: Check PDF structure
    print("🔍 Test 1: PDF Structure Check")
    print("-" * 50)
    try:
        with open(pdf_file, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            num_pages = len(pdf_reader.pages)
            print(f"   ✓ Valid PDF with {num_pages} pages")
            
            # Check if encrypted
            if pdf_reader.is_encrypted:
                print(f"   ⚠️  PDF is encrypted")
            
            # Check first page details
            page = pdf_reader.pages[0]
            print(f"\n   Page 1 Info:")
            print(f"   - Page object: {page}")
            print(f"   - Resources: {'Available' if '/Resources' in page else 'Not found'}")
            print(f"   - Contents: {'Available' if '/Contents' in page else 'Not found'}")
            
    except Exception as e:
        print(f"   ❌ Error reading PDF: {e}")
        return
    
    # Test 2: Extract text from each page
    print("\n🔍 Test 2: Native Text Extraction")
    print("-" * 50)
    try:
        with open(pdf_file, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_text = ""
            
            for page_num, page in enumerate(pdf_reader.pages[:3]):  # First 3 pages
                text = page.extract_text()
                total_text += text + "\n"
                text_len = len(text.strip())
                print(f"   Page {page_num + 1}: {text_len} characters")
                if text_len > 0:
                    print(f"      Sample: {text[:100].strip()}...")
            
            total_len = len(total_text.strip())
            if total_len == 0:
                print(f"\n   ⚠️  PDF has NO native text - it's a scanned image!")
            else:
                print(f"\n   ✓ Extracted {total_len} total characters")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 3: Try to convert to images
    print("\n🔍 Test 3: Convert to Images (OCR candidate)")
    print("-" * 50)
    try:
        images = convert_from_path(str(pdf_file), first_page=1, last_page=1)
        print(f"   ✓ Successfully converted to {len(images)} image(s)")
        print(f"   - First image: {images[0].size} pixels")
        
        # Save image for manual inspection
        img_path = pdf_file.parent / "page_1_sample.png"
        images[0].save(img_path, 'PNG')
        print(f"   - Saved sample to: {img_path}")
        
    except Exception as e:
        print(f"   ⚠️  Error converting: {e}")
    
    # Test 4: Try OCR on the image
    print("\n🔍 Test 4: OCR Test")
    print("-" * 50)
    try:
        import pytesseract
        images = convert_from_path(str(pdf_file), first_page=1, last_page=1)
        if images:
            ocr_text = pytesseract.image_to_string(images[0])
            ocr_len = len(ocr_text.strip())
            print(f"   ✓ OCR extracted {ocr_len} characters")
            if ocr_len > 0:
                print(f"   Sample: {ocr_text[:100].strip()}...")
            else:
                print(f"   ⚠️  OCR found no text - image may be blank or too low quality")
    except Exception as e:
        print(f"   ⚠️  OCR error: {e}")
    
    print("\n" + "="*70)
    print("📊 DIAGNOSIS CONCLUSION:")
    print("="*70)
    
    # Summary
    with open(pdf_file, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        num_pages = len(pdf_reader.pages)
        
        # Try to extract from first page
        page = pdf_reader.pages[0]
        first_page_text = page.extract_text()
        
        if len(first_page_text.strip()) > 100:
            print("✅ PDF has embedded text - extraction should work")
            print("   → Use: extract_text_from_pdf(use_ocr=False)")
        elif len(first_page_text.strip()) > 0:
            print("⚠️  PDF has minimal text - OCR will help")
            print("   → Use: extract_text_from_pdf(use_ocr=True)")
        else:
            print("❌ PDF is SCANNED IMAGE - needs OCR or AI")
            print("   → Issue: Names won't extract properly")
            print("   → Solution: Enable OCR or AI extraction")
            print(f"   → Total pages: {num_pages}")

if __name__ == '__main__':
    diagnose_pdf()
