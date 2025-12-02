#!/usr/bin/env python3
"""
Test mismatch detection with dummy data
"""
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.mismatch_detector import MismatchDetector

def test_mismatch_detection():
    """Test mismatch detection with dummy data"""
    
    print("\n" + "="*60)
    print("🧪 MISMATCH DETECTION TEST")
    print("="*60 + "\n")
    
    # Dummy company profile
    company_profile = {
        'company_number': '12345678',
        'company_name': 'TEST COMPANY LIMITED',
        'previous_company_names': [
            {'name': 'OLD NAME LIMITED'}
        ]
    }
    
    filing_data = {'items': []}
    
    # Dummy parsed documents - with names that DON'T match
    parsed_documents = [
        {
            'success': True,
            'file_name': 'incorporation_12345678.pdf',
            'document_type': 'incorporation',
            'names': ['ORIGINAL COMPANY NAME LIMITED', 'TEST COMPANY LIMITED'],
            'text_length': 1000
        },
        {
            'success': True,
            'file_name': 'name_change_12345678.pdf',
            'document_type': 'name_change',
            'names': ['HIDDEN NAME LTD', 'TEST COMPANY LIMITED'],
            'text_length': 800
        }
    ]
    
    print(f"📋 Test Data:")
    print(f"   Company: {company_profile['company_name']} ({company_profile['company_number']})")
    print(f"   Official Names: {[company_profile['company_name']] + [p['name'] for p in company_profile.get('previous_company_names', [])]}")
    print(f"   Documents: {len(parsed_documents)}")
    print()
    
    # Run mismatch detection
    detector = MismatchDetector()
    result = detector.detect_mismatches(company_profile, filing_data, parsed_documents)
    
    print(f"✅ Mismatch Detection Result:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*60)
    if result.get('mismatches'):
        print(f"✅ SUCCESS: Found {len(result['mismatches'])} mismatch(es)")
        for i, mismatch in enumerate(result['mismatches'], 1):
            print(f"\n   Mismatch #{i}:")
            print(f"   Type: {mismatch.get('type')}")
            print(f"   Severity: {mismatch.get('severity')}")
            print(f"   Message: {mismatch.get('message', 'N/A')[:200]}...")
    else:
        print("❌ ERROR: No mismatches found (should have found some!)")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_mismatch_detection()
