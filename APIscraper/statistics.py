
"""Entity statistics utilities for analyzing extracted entities."""

from collections import Counter
from pathlib import Path


def get_entity_statistics(out_dir: str) -> Counter:
    """Count entity types from all .txt files in the output directory.
    
    Args:
        out_dir: Directory containing .txt files with entity annotations
        
    Returns:
        Counter: Counter of entity types {entity_type: count}
    """
    entity_counter = Counter()
    txt_files = list(Path(out_dir).glob("*.txt"))
    
    for txt_file in txt_files:
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Skip first two lines (title and abstract), process entity lines
                for line in lines[2:]:
                    parts = line.strip().split("\t")
                    # Entity lines format: PMID\tstart\tend\tmention\ttype\tid
                    if len(parts) >= 5:
                        entity_type = parts[4]  # 5th column is entity type
                        if entity_type:  # Only count non-empty types
                            entity_counter[entity_type] += 1
        except (IOError, IndexError):
            # Skip files that can't be read or don't match format
            continue
    
    return entity_counter


def print_entity_statistics(entity_counter: Counter, out_dir: str) -> None:
    """Print formatted statistics of entity types.
    
    Args:
        entity_counter: Counter of entity types
        out_dir: Output directory path
    """
    if not entity_counter:
        print("\nNo entity statistics available (no entities found in files).")
        return
    
    print("\n" + "="*70)
    print("ENTITY TYPE STATISTICS")
    print("="*70)
    print(f"{'Count':<10} {'Entity Type':<20}")
    print("-"*70)
    
    # Sort by count (descending)
    for entity_type, count in entity_counter.most_common():
        print(f"{count:<10} {entity_type:<20}")
    
    total_entities = sum(entity_counter.values())
    total_files = len(list(Path(out_dir).glob("*.txt")))
    print("-"*70)
    print(f"Total entities: {total_entities}")
    print(f"Total files analyzed: {total_files}")
    print(f"Output directory: {out_dir}")
    print("="*70 + "\n")
