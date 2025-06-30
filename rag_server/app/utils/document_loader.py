# app/utils/document_loader.py
from typing import List, Optional

from langchain_core.documents import Document

from app.config import known_source_ext, PDF_EXTRACT_IMAGES, CHUNK_OVERLAP
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredEPubLoader,
    UnstructuredMarkdownLoader,
    UnstructuredXMLLoader,
    UnstructuredRSTLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
)

def get_loader(filename: str, file_content_type: str, filepath: str):
    file_ext = filename.split(".")[-1].lower()
    known_type = True

    if file_ext == "pdf":
        loader = PyPDFLoader(filepath, extract_images=PDF_EXTRACT_IMAGES)
    elif file_ext == "csv":
        loader = CSVLoader(filepath)
    elif file_ext == "rst":
        loader = UnstructuredRSTLoader(filepath, mode="elements")
    elif file_ext == "xml":
        loader = UnstructuredXMLLoader(filepath)
    elif file_ext == "pptx":
        loader = UnstructuredPowerPointLoader(filepath)
    elif file_ext == "md":
        loader = UnstructuredMarkdownLoader(filepath)
    elif file_content_type == "application/epub+zip":
        loader = UnstructuredEPubLoader(filepath)
    elif (
        file_content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or file_ext in ["doc", "docx"]
    ):
        loader = Docx2txtLoader(filepath)
    elif file_content_type in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ] or file_ext in ["xls", "xlsx"]:
        loader = UnstructuredExcelLoader(filepath)
    elif file_content_type == "application/json" or file_ext == "json":
        loader = TextLoader(filepath, autodetect_encoding=True)
    elif file_ext in known_source_ext or (
        file_content_type and file_content_type.find("text/") >= 0
    ):
        loader = TextLoader(filepath, autodetect_encoding=True)
    else:
        loader = TextLoader(filepath, autodetect_encoding=True)
        known_type = False

    return loader, known_type, file_ext

def enhance_document_metadata(documents: List[Document], filename: str, file_ext: str) -> List[Document]:
    """
    Enhance documents with better metadata including file type classification.
    
    :param documents: List of documents to enhance
    :param filename: Original filename
    :param file_ext: File extension
    :return: Documents with enhanced metadata
    """
    # File type mappings
    code_extensions = {
        'py', 'js', 'ts', 'tsx', 'jsx', 'java', 'cpp', 'c', 'h', 'cs', 'php', 
        'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'r', 'm', 'mm', 'sql', 
        'sh', 'bash', 'ps1', 'lua', 'pl', 'dart', 'vue', 'svelte'
    }
    
    doc_extensions = {
        'md', 'txt', 'rst', 'adoc', 'tex', 'doc', 'docx', 'pdf'
    }
    
    config_extensions = {
        'json', 'yaml', 'yml', 'toml', 'ini', 'conf', 'cfg', 'env', 
        'properties', 'xml', 'plist', 'dockerfile'
    }
    
    test_patterns = {
        'test_', '_test', '.test.', '.spec.', 'tests/', 'test/', 
        '__tests__/', 'spec/', 'cypress/', 'e2e/'
    }
    
    # Determine document type
    filename_lower = filename.lower()
    
    if any(pattern in filename_lower for pattern in test_patterns):
        doc_type = "test"
    elif file_ext in code_extensions:
        doc_type = "code"
    elif file_ext in doc_extensions:
        doc_type = "documentation"
    elif file_ext in config_extensions:
        doc_type = "configuration"
    else:
        doc_type = "other"
    
    # Determine programming language for code files
    language = None
    if doc_type == "code":
        language_map = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript', 
            'java': 'java', 'cpp': 'cpp', 'c': 'c', 'cs': 'csharp',
            'php': 'php', 'rb': 'ruby', 'go': 'go', 'rs': 'rust',
            'swift': 'swift', 'kt': 'kotlin', 'scala': 'scala',
            'sql': 'sql', 'sh': 'shell', 'bash': 'shell'
        }
        language = language_map.get(file_ext, file_ext)
    
    # Enhance each document with metadata
    for doc in documents:
        doc.metadata.update({
            'file_type': doc_type,
            'file_extension': file_ext,
            'language': language,
            'filename': filename,
            'document_category': doc_type  # For compatibility
        })
    
    return documents

def clean_text(text: str) -> str:
    """
    Remove NUL (0x00) characters from a string.

    :param text: The original text with potential NUL characters.
    :return: Cleaned text without NUL characters.
    """
    return text.replace("\x00", "")

def process_documents(documents: List[Document]) -> str:
    processed_text = ""
    last_page: Optional[int] = None
    doc_basename = ""

    for doc in documents:
        if "source" in doc.metadata:
            doc_basename = doc.metadata["source"].split("/")[-1]
            break

    processed_text += f"{doc_basename}\n"

    for doc in documents:
        current_page = doc.metadata.get("page")
        if current_page and current_page != last_page:
            processed_text += f"\n# PAGE {doc.metadata['page']}\n\n"
            last_page = current_page

        new_content = doc.page_content
        if processed_text.endswith(new_content[:CHUNK_OVERLAP]):
            processed_text += new_content[CHUNK_OVERLAP:]
        else:
            processed_text += new_content

    return processed_text.strip()