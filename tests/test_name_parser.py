"""
Tests for name parser
"""
import pytest
from parsers.name_parser import NameParser


def test_normalize_name():
    """Test name normalization"""
    parser = NameParser()
    
    # Test basic normalization
    assert parser.normalize_name("ACME LTD") == "ACME LIMITED"
    assert parser.normalize_name("acme limited") == "ACME LIMITED"
    assert parser.normalize_name("ACME  LIMITED") == "ACME LIMITED"


def test_compare_names():
    """Test name comparison"""
    parser = NameParser()
    
    # Exact match
    similarity, is_match = parser.compare_names("ACME LIMITED", "ACME LIMITED")
    assert is_match is True
    assert similarity == 1.0
    
    # Similar names
    similarity, is_match = parser.compare_names("ACME LTD", "ACME LIMITED")
    assert is_match is True
    
    # Different names
    similarity, is_match = parser.compare_names("ACME LIMITED", "XYZ LIMITED")
    assert is_match is False


def test_extract_names():
    """Test name extraction from text"""
    parser = NameParser()
    
    text = """
    Certificate of Incorporation
    
    Company Name: ACME TRADING LIMITED
    
    This certifies that the company was incorporated on 01/01/2020.
    """
    
    names = parser.extract_names(text)
    assert len(names) > 0
    assert any("ACME TRADING LIMITED" in name for name in names)


if __name__ == '__main__':
    pytest.main([__file__])
