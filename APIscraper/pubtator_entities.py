# Reference - this script involves the use of Cursor AI https://cursor.com

"""
Fetch PubTator3 entity annotations for a PubMed PMID.

Output format: PMID<TAB>start<TAB>end<TAB>mention<TAB>EntityType<TAB>EntityID
"""

import os
import sys

import requests


def fetch_pubtator_annotations(pmid: str) -> dict:
    """Fetch PubTator3 BioC JSON annotations for a given PMID."""
    url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson?pmids={pmid}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data


def extract_title_and_abstract(bioc_data: dict) -> tuple[str, str]:
    """Extract title and abstract text from BioC JSON."""
    title = ""
    abstract = ""
    
    # PubTator3 API returns {"PubTator3": [document, ...]}
    documents = bioc_data.get("PubTator3", [])
    
    for document in documents:
        for passage in document.get("passages", []):
            infon_type = passage.get("infons", {}).get("type", "")
            text = passage.get("text", "")
            
            if infon_type == "title":
                title = text
            elif infon_type == "abstract":
                abstract = text
    
    return title, abstract


def extract_entities(bioc_data: dict, title: str, abstract: str) -> list[dict]:
    """Extract entities from BioC JSON and calculate global offsets."""
    full_text = title + "\n" + abstract
    entities = []
    
    # PubTator3 API returns {"PubTator3": [document, ...]}
    documents = bioc_data.get("PubTator3", [])
    
    for document in documents:
        for passage in document.get("passages", []):
            infon_type = passage.get("infons", {}).get("type", "")
            
            # Only process title and abstract passages
            if infon_type not in ("title", "abstract"):
                continue
            
            # Get annotations in this passage
            for annotation in passage.get("annotations", []):
                # Get location (offset and length)
                locations = annotation.get("locations", [])
                if not locations:
                    continue
                
                # PubTator3 API returns global offsets in annotations
                global_start = locations[0].get("offset", 0)
                local_length = locations[0].get("length", 0)
                global_end = global_start + local_length
                
                # Get entity text
                mention = annotation.get("text", "")
                if not mention:
                    mention = full_text[global_start:global_end]
                
                # Get entity type and ID
                infons = annotation.get("infons", {})
                entity_type = infons.get("type", "").strip()
                entity_id = infons.get("identifier", "").strip()
                
                # Skip if missing required fields (entity_id is required)
                if not entity_type or not entity_id:
                    continue
                
                entities.append({
                    "start": global_start,
                    "end": global_end,
                    "mention": mention,
                    "type": entity_type,
                    "id": entity_id
                })
    
    return entities


def append_entities_to_file(pmid: str, out_dir: str) -> bool:
    """Fetch PubTator entities for a PMID and append them to the article file.
    Deletes the file if no entities are found or if fetching fails.
    This ensures only files with entity annotations are kept when --no-entities is not used.
    
    Returns:
        bool: True if entities were successfully added, False if file was deleted
    """
    file_path = os.path.join(out_dir, f"{pmid}.txt")
    if not os.path.exists(file_path):
        return False
    
    try:
        bioc_data = fetch_pubtator_annotations(pmid)
        title, abstract = extract_title_and_abstract(bioc_data)
        
        if not title and not abstract:
            os.remove(file_path)
            print(f"  Deleted {pmid}.txt: No title/abstract found in PubTator")
            return False
        
        entities = extract_entities(bioc_data, title, abstract)
        
        if not entities:
            os.remove(file_path)
            print(f"  Deleted {pmid}.txt: No entities found")
            return False
        
        with open(file_path, "a", encoding="utf-8") as f:
            for entity in entities:
                f.write(
                    f"{pmid}\t{entity['start']}\t{entity['end']}\t"
                    f"{entity['mention']}\t{entity['type']}\t{entity['id']}\n"
                )
        
        print(f"  Added {len(entities)} entities to {pmid}.txt")
        return True
    
    except Exception as e:
        os.remove(file_path)
        print(f"  Deleted {pmid}.txt: Failed to fetch entities ({e})", file=sys.stderr)
        return False
        
# end of reference
