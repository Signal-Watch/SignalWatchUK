"""
Name Parser - Extracts and normalizes company names from text
"""
import re
from typing import List, Set, Optional, Tuple
from difflib import SequenceMatcher


class NameParser:
    """Extract and normalize company names from text"""
    
    # Common company suffixes
    SUFFIXES = [
        'LIMITED', 'LTD', 'LTD.', 
        'PLC', 'P.L.C.', 'PUBLIC LIMITED COMPANY',
        'LLP', 'LIMITED LIABILITY PARTNERSHIP',
        'LP', 'LIMITED PARTNERSHIP',
        'CIC', 'COMMUNITY INTEREST COMPANY',
        'CIO', 'CHARITABLE INCORPORATED ORGANISATION',
        'CHARITY', 'UNLTD', 'UNLIMITED'
    ]
    
    # Patterns for finding company names
    NAME_PATTERNS = [
        # Certificate of incorporation - most reliable
        r'(?:company name|name of company|corporate name)[:\s]+([A-Z][A-Z\s&\'-]+(?:LIMITED|LTD|PLC|LLP|CIC|CHARITY)?)',
        
        # Change of name - also reliable
        r'(?:changed its name (?:to|from)|new name|former name|previous name)[:\s]+([A-Z][A-Z\s&\'-]+(?:LIMITED|LTD|PLC|LLP)?)',
        
        # Incorporation lines with company names
        r'^([A-Z][A-Z\s&\'-]{8,}(?:LIMITED|LTD|PLC|LLP))(?:\s|$)',
        
        # In "company" context (must have more strict requirements)
        r'(?:company[:\s]+)([A-Z][A-Z\s&\'-]{5,}(?:LIMITED|LTD|PLC|LLP|CIC))',
    ]
    
    def extract_names(self, text: str) -> List[str]:
        """
        Extract company names from text
        
        Args:
            text: Text to search
            
        Returns:
            List of unique company names found
        """
        names = set()
        
        # Try each pattern
        for pattern in self.NAME_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                name = match.group(1).strip()
                if self._is_valid_name(name):
                    names.add(self.normalize_name(name))
        
        # Also look for names in specific document sections
        section_names = self._extract_from_sections(text)
        names.update(section_names)
        
        return list(names)
    
    def _extract_from_sections(self, text: str) -> Set[str]:
        """
        Extract names from specific document sections
        
        Args:
            text: Document text
            
        Returns:
            Set of company names
        """
        names = set()
        
        # Look for "Name of Company" field
        name_field = re.search(
            r'(?:Name of [Cc]ompany|Company [Nn]ame)[:\s]*\n?\s*([A-Z][^\n]{5,100})',
            text
        )
        if name_field:
            potential_name = name_field.group(1).strip()
            # Extract up to the first suffix
            for suffix in self.SUFFIXES:
                idx = potential_name.upper().find(suffix)
                if idx != -1:
                    name = potential_name[:idx + len(suffix)]
                    if self._is_valid_name(name):
                        names.add(self.normalize_name(name))
                    break
        
        return names
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Check if extracted text is likely a valid company name
        
        Args:
            name: Potential company name
            
        Returns:
            True if valid
        """
        if not name or len(name) < 5:
            return False
        
        # Must contain at least one suffix
        name_upper = name.upper()
        has_suffix = any(suffix in name_upper for suffix in self.SUFFIXES)
        if not has_suffix:
            return False
        
        # Should be mostly letters (allow for OCR errors)
        letter_count = sum(c.isalpha() or c.isspace() for c in name)
        if letter_count / len(name) < 0.6:
            return False
        
        # Shouldn't be too long (probably not a name)
        if len(name) > 150:
            return False
        
        # Shouldn't contain certain words (expanded list)
        invalid_words = [
            'HEREBY', 'CERTIFY', 'REGISTRAR', 'SECRETARY', 'PURSUANT',
            'CERTIFICATE', 'INCORPORATION', 'DECLARATION', 'STATEMENT',
            'FORM', 'SECTION', 'ARTICLE', 'CLAUSE', 'PARAGRAPH',
            'GUARANTEE', 'MEMORANDUM', 'ASSOCIATION', 'CAPITAL', 'SHARE',
            'COMPANIES ACT', 'REGISTERED', 'OFFICE', 'NUMBER', 'COMPANY NO',
            'REGISTERED OFFICE', 'ADDRESS'
        ]
        if any(word in name_upper for word in invalid_words):
            return False
        
        # Shouldn't be just a suffix
        if name_upper.strip() in self.SUFFIXES:
            return False
        
        # Must have at least 2 words (company names usually have multiple words)
        word_count = len(name.split())
        if word_count < 2:
            return False
        
        return True
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize company name for comparison
        
        Args:
            name: Raw company name
            
        Returns:
            Normalized name
        """
        # Convert to uppercase
        name = name.upper().strip()
        
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name)
        
        # Standardize suffixes
        replacements = {
            'LTD.': 'LIMITED',
            'LTD': 'LIMITED',
            'P.L.C.': 'PLC',
            'L.L.P.': 'LLP',
        }
        
        for old, new in replacements.items():
            if name.endswith(old):
                name = name[:-len(old)] + new
        
        # Remove punctuation except &
        name = re.sub(r'[^\w\s&]', '', name)
        
        # Remove extra spaces
        name = ' '.join(name.split())
        
        return name
    
    def compare_names(self, name1: str, name2: str) -> Tuple[float, bool]:
        """
        Compare two company names and determine if they match
        
        Args:
            name1: First company name
            name2: Second company name
            
        Returns:
            Tuple of (similarity_score, is_match)
        """
        # Normalize both names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        # Exact match
        if norm1 == norm2:
            return (1.0, True)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Consider match if very similar (lowered threshold for better detection)
        is_match = similarity >= 0.85
        
        # Also check if one is a substring of the other (with suffix)
        if not is_match:
            # Remove suffixes for comparison
            base1 = self._remove_suffix(norm1)
            base2 = self._remove_suffix(norm2)
            
            if base1 and base2:
                # Check substring match
                if base1 in base2 or base2 in base1:
                    is_match = True
                    similarity = max(similarity, 0.82)
                # Check word-level similarity (handles word order changes)
                else:
                    words1 = set(base1.split())
                    words2 = set(base2.split())
                    if words1 and words2:
                        word_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                        if word_similarity >= 0.75:
                            is_match = True
                            similarity = max(similarity, word_similarity)
        
        return (similarity, is_match)
    
    def _remove_suffix(self, name: str) -> str:
        """
        Remove company suffix from name
        
        Args:
            name: Company name
            
        Returns:
            Name without suffix
        """
        name_upper = name.upper()
        for suffix in sorted(self.SUFFIXES, key=len, reverse=True):
            if name_upper.endswith(suffix):
                return name[:-len(suffix)].strip()
        return name
    
    def extract_name_changes(self, text: str) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        Extract name change information (from -> to)
        
        Args:
            text: Document text
            
        Returns:
            List of (old_name, new_name) tuples
        """
        changes = []
        
        # Pattern: "changed its name from X to Y"
        pattern1 = r'changed its name from\s+([A-Z][^\n]{10,100})\s+to\s+([A-Z][^\n]{10,100})'
        matches = re.finditer(pattern1, text, re.IGNORECASE)
        for match in matches:
            old_name = match.group(1).strip()
            new_name = match.group(2).strip()
            
            # Extract actual names (up to suffix)
            old_name = self._extract_name_with_suffix(old_name)
            new_name = self._extract_name_with_suffix(new_name)
            
            if old_name and new_name:
                changes.append((
                    self.normalize_name(old_name),
                    self.normalize_name(new_name)
                ))
        
        # Pattern: "former name: X, new name: Y"
        pattern2 = r'former name[:\s]+([A-Z][^\n]{10,100})[\s\n]+new name[:\s]+([A-Z][^\n]{10,100})'
        matches = re.finditer(pattern2, text, re.IGNORECASE)
        for match in matches:
            old_name = self._extract_name_with_suffix(match.group(1).strip())
            new_name = self._extract_name_with_suffix(match.group(2).strip())
            
            if old_name and new_name:
                changes.append((
                    self.normalize_name(old_name),
                    self.normalize_name(new_name)
                ))
        
        return changes
    
    def _extract_name_with_suffix(self, text: str) -> Optional[str]:
        """
        Extract name from text, ensuring it includes a suffix
        
        Args:
            text: Text containing name
            
        Returns:
            Extracted name or None
        """
        for suffix in sorted(self.SUFFIXES, key=len, reverse=True):
            idx = text.upper().find(suffix)
            if idx != -1:
                name = text[:idx + len(suffix)]
                if self._is_valid_name(name):
                    return name
        return None
