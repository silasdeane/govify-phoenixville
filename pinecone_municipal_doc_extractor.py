#!/usr/bin/env python3
"""
General document information extractor for municipal documents.
This script analyzes uploaded documents to identify and extract structured information
like committees, boards, officials, and other key entities to improve retrieval.
"""

import os
import re
import glob
from typing import Dict, List, Any, Optional
from pinecone import Pinecone
import uuid
from langchain.document_loaders import TextLoader
from lanchain_pinecone_adapter import CustomHuggingFaceEmbeddings

# Load environment variables
pinecone_api_key = os.environ.get('PINECONE_API_KEY', 'pcsk_1MfLA_QRmNnRSR4pumc7thAYp6eqHkxGF3Jhmbs9X66SN2i1Rr4akBzmERV5NCjyBhE8e')
index_name = os.environ.get('PINECONE_INDEX_NAME', 'phoenixville-municipal-code')
source_directory = os.environ.get('SOURCE_DIRECTORY', 'source_documents')

class DocumentAnalyzer:
    """General document analyzer that extracts structured information"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = self._load_content()
        self.filename = os.path.basename(file_path)
        self.doc_type = self._detect_document_type()
    
    def _load_content(self) -> str:
        """Load document content"""
        if not os.path.exists(self.file_path):
            print(f"File not found: {self.file_path}")
            return ""
        
        try:
            with open(self.file_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {self.file_path}: {e}")
            return ""
    
    def _detect_document_type(self) -> str:
        """Detect the type of document based on content and filename"""
        filename_lower = self.filename.lower()
        content_sample = self.content[:1000].lower()  # Look at first 1000 chars
        
        # Check for board/committee documents
        if any(term in content_sample for term in ['board', 'committee', 'commission', 'council']):
            if 'zoning' in content_sample or 'zoning' in filename_lower:
                return 'zoning_board'
            elif 'planning' in content_sample or 'planning' in filename_lower:
                return 'planning_commission'
            elif 'council' in content_sample or 'council' in filename_lower:
                return 'borough_council'
            else:
                return 'committee'
        
        # Check for code/ordinance documents
        if any(term in content_sample for term in ['code', 'ordinance', 'regulation', 'law']):
            if 'zoning' in content_sample or 'zoning' in filename_lower:
                return 'zoning_code'
            else:
                return 'municipal_code'
        
        # Check for minutes/agendas
        if any(term in content_sample for term in ['minutes', 'agenda', 'meeting']):
            return 'meeting_document'
        
        # General information documents
        if any(term in content_sample for term in ['about', 'info', 'guide', 'facts']):
            return 'information'
            
        # Default to general document
        return 'general'
    
    def extract_people(self) -> Dict[str, List[str]]:
        """Extract people mentioned in the document with their roles"""
        people = {
            'officials': [],
            'board_members': [],
            'staff': [],
            'chairs': [],
            'secretaries': []
        }
        
        # Look for officials, chairs, etc. with pattern: Role: Name
        role_patterns = [
            (r"(?:Chair|Chairman|Chairperson|President):\s*([\w\s]+)(?=\n)", 'chairs'),
            (r"(?:Secretary|Clerk):\s*([\w\s]+)(?=\n)", 'secretaries'),
            (r"(?:Mayor|Manager|Director|Administrator|Supervisor):\s*([\w\s]+)(?=\n)", 'officials')
        ]
        
        for pattern, category in role_patterns:
            matches = re.findall(pattern, self.content)
            for match in matches:
                name = match.strip()
                if name and name not in people[category]:
                    people[category].append(name)
        
        # Look for board members in lists
        member_section = re.search(r"(?:Members|Board Members|Committee Members):(.*?)(?=\n\n|\n[A-Z]|\Z)", 
                                 self.content, re.DOTALL | re.IGNORECASE)
        if member_section:
            member_lines = member_section.group(1).strip().split('\n')
            for line in member_lines:
                # Clean the line and check if it looks like a list item
                clean_line = line.strip()
                if clean_line.startswith('−') or clean_line.startswith('-') or clean_line.startswith('–'):
                    member = clean_line[1:].strip()
                    if member and member not in people['board_members']:
                        people['board_members'].append(member)
        
        return people
    
    def extract_dates(self) -> Dict[str, Any]:
        """Extract important dates from the document"""
        dates = {
            'meeting_dates': [],
            'deadlines': [],
            'effective_dates': []
        }
        
        # Look for meeting dates
        meeting_patterns = [
            r"meet(?:s|ings?) (?:on|every|each) ([\w\s,]+)",
            r"meetings?: ([\w\s,]+)"
        ]
        
        for pattern in meeting_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip() not in dates['meeting_dates']:
                    dates['meeting_dates'].append(match.strip())
        
        # Look for effective dates for ordinances, etc.
        effective_pattern = r"effective(?:\s+date)?(?:\s+on)?(?:\s+of)?: ([\w\s,]+)"
        matches = re.findall(effective_pattern, self.content, re.IGNORECASE)
        for match in matches:
            if match.strip() and match.strip() not in dates['effective_dates']:
                dates['effective_dates'].append(match.strip())
        
        return dates
    
    def extract_purpose(self) -> Optional[str]:
        """Extract purpose statement from document"""
        purpose_patterns = [
            r"(?:Purpose|Mission|Responsibilities|Function):(.*?)(?=\n\n|\n[A-Z]|\Z)",
            r"(?:Purpose|Mission|Responsibilities|Function) (?:of|for) .*?:(.*?)(?=\n\n|\n[A-Z]|\Z)",
            r"(?:responsible for|duties include) (.*?)(?=\n\n|\n[A-Z]|\Z)"
        ]
        
        for pattern in purpose_patterns:
            match = re.search(pattern, self.content, re.DOTALL | re.IGNORECASE)
            if match:
                purpose = match.group(1).strip()
                return purpose
        
        return None
    
    def extract_locations(self) -> List[str]:
        """Extract location information from document"""
        locations = []
        
        # Common location patterns
        location_patterns = [
            r"(?:Location|Address|Place|Venue):\s*([\w\s,\.]+)(?=\n)",
            r"(?:located at|held at|takes place at) ([\w\s,\.]+)(?=\n|\.)",
            r"(?:\d+) ([\w\s]+(?:Street|St\.|Avenue|Ave\.|Road|Rd\.|Drive|Dr\.|Lane|Ln\.|Place|Pl\.|Boulevard|Blvd\.)[\w\s,\.]*)"
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            for match in matches:
                location = match.strip()
                if location and location not in locations:
                    locations.append(location)
        
        return locations
    
    def extract_all_info(self) -> Dict[str, Any]:
        """Extract all relevant information from the document"""
        info = {
            'filename': self.filename,
            'document_type': self.doc_type,
            'source_file': self.file_path
        }
        
        # Extract people information
        people = self.extract_people()
        for category, people_list in people.items():
            if people_list:
                info[category] = people_list
        
        # Extract dates
        dates = self.extract_dates()
        for date_type, date_list in dates.items():
            if date_list:
                info[date_type] = date_list
        
        # Extract purpose
        purpose = self.extract_purpose()
        if purpose:
            info['purpose'] = purpose
        
        # Extract locations
        locations = self.extract_locations()
        if locations:
            info['locations'] = locations
        
        return info

def add_structured_info_to_pinecone(doc_info):
    """Add structured document information to Pinecone"""
    if not doc_info or 'document_type' not in doc_info:
        print("No valid document information to add")
        return
    
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(index_name)
    
    # Initialize embeddings
    try:
        embeddings = CustomHuggingFaceEmbeddings()
    except Exception as e:
        print(f"Error initializing custom embeddings: {e}")
        from langchain.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Create a structured document for better retrieval
    structured_doc = f"""
    Document Type: {doc_info['document_type']}
    Filename: {doc_info['filename']}
    """
    
    # Add people information
    if 'chairs' in doc_info and doc_info['chairs']:
        structured_doc += f"\nChair(s): {', '.join(doc_info['chairs'])}"
    
    if 'secretaries' in doc_info and doc_info['secretaries']:
        structured_doc += f"\nSecretary(s): {', '.join(doc_info['secretaries'])}"
    
    if 'officials' in doc_info and doc_info['officials']:
        structured_doc += f"\nOfficials: {', '.join(doc_info['officials'])}"
    
    if 'board_members' in doc_info and doc_info['board_members']:
        structured_doc += f"\nBoard/Committee Members: {', '.join(doc_info['board_members'])}"
    
    # Add purpose
    if 'purpose' in doc_info and doc_info['purpose']:
        structured_doc += f"\nPurpose: {doc_info['purpose']}"
    
    # Add meeting dates
    if 'meeting_dates' in doc_info and doc_info['meeting_dates']:
        structured_doc += f"\nMeeting Dates: {', '.join(doc_info['meeting_dates'])}"
    
    # Add locations
    if 'locations' in doc_info and doc_info['locations']:
        structured_doc += f"\nLocations: {', '.join(doc_info['locations'])}"
    
    # Create embedding for this document
    embedding = embeddings.embed_query(structured_doc)
    
    # Create metadata with specialized fields for better retrieval
    # First convert any lists to strings for Pinecone compatibility
    metadata = {}
    for key, value in doc_info.items():
        if isinstance(value, list):
            metadata[key] = ", ".join(value)
        else:
            metadata[key] = value
    
    # Add the full structured document for retrieval
    metadata['text'] = structured_doc
    
    # Create vector to upsert
    vector = {
        'id': f"{doc_info['document_type']}-{uuid.uuid4()}",
        'values': embedding,
        'metadata': metadata
    }
    
    # Upsert to Pinecone
    index.upsert(vectors=[vector])
    print(f"Added structured information for {doc_info['filename']} to Pinecone")

def process_all_documents():
    """Process all documents in the source directory"""
    # Get all text files in the source directory
    all_files = []
    for ext in ['.txt', '.md', '.csv']:
        all_files.extend(glob.glob(os.path.join(source_directory, f"**/*{ext}"), recursive=True))
    
    print(f"Found {len(all_files)} documents to analyze")
    
    for file_path in all_files:
        print(f"\nAnalyzing {os.path.basename(file_path)}...")
        analyzer = DocumentAnalyzer(file_path)
        doc_info = analyzer.extract_all_info()
        
        # Print summary of extracted information
        print(f"  Document Type: {doc_info['document_type']}")
        if 'board_members' in doc_info and doc_info['board_members']:
            print(f"  Found {len(doc_info['board_members'])} board/committee members")
        if 'purpose' in doc_info:
            print(f"  Found purpose statement")
        
        # Add to Pinecone
        add_structured_info_to_pinecone(doc_info)

def main():
    """Extract and add structured information from all documents to Pinecone"""
    print("Starting document analysis...")
    
    # Process all documents
    process_all_documents()
    
    print("\nDocument analysis complete!")

if __name__ == "__main__":
    main()