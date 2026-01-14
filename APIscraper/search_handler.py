
"""Search handler for finding articles with entities until target count is reached."""

from typing import List, Tuple

from pubmed_fetcher import PubMedFetcher, chunked, save_article_txt
from pubtator_entities import append_entities_to_file


def test_entity_availability(query: str, test_batch_size: int, batch_size: int, 
                            out_dir: str, email: str) -> Tuple[bool, str, List[str], int, int]:
    """Test initial query to check if articles have entities available.
    
    Args:
        query: PubMed search query
        test_batch_size: Number of articles to test (e.g., 20)
        batch_size: Batch size for API requests
        out_dir: Output directory for saved files
        email: Email for API identification
        
    Returns:
        tuple: (use_older_articles, current_query, articles_saved, success_count, failure_count)
    """
    print(f"Testing first {test_batch_size} articles to check entity availability...")
    test_fetcher = PubMedFetcher(query=query, max_results=test_batch_size, email=email)
    test_pmids = test_fetcher.fetch_pmids(retstart=0, retmax=test_batch_size)
    
    articles_saved = []
    test_success = 0
    test_fail = 0
    processed_pmids = set()
    
    if not test_pmids:
        return False, query, articles_saved, test_success, test_fail
    
    # Process test batch
    for batch in chunked(test_pmids[:test_batch_size], batch_size):
        xml_text = test_fetcher.fetch_records(batch)
        test_articles = test_fetcher.parse_xml(xml_text)
        
        for art in test_articles:
            if art["pmid"] in processed_pmids:
                continue
            
            processed_pmids.add(art["pmid"])
            
            save_article_txt(art, out_dir)
            success = append_entities_to_file(art["pmid"], out_dir)
            
            if success:
                test_success += 1
                articles_saved.append(art["pmid"])
            else:
                test_fail += 1
    
    # Calculate failure rate and decide
    test_total = test_success + test_fail
    if test_total >= 5:
        failure_rate = test_fail / test_total if test_total > 0 else 0
        
        if failure_rate > 0.8:
            # More than 80% failed - switch to older articles immediately
            print(f"\n{'='*70}")
            print(f"WARNING: Entity fetching failed for {test_fail}/{test_total} articles (>80% failure rate)")
            print("Articles are likely too recent and don't have PubTator annotations yet.")
            print(f"Successfully got entities: {test_success}/{test_total}")
            print(f"\nAUTOMATIC FALLBACK: Switching to older articles (2021-2023) that have PubTator annotations...")
            print(f"{'='*70}\n")
            
            current_query = f"{query} AND (2023[PDAT] OR 2022[PDAT] OR 2021[PDAT])"
            return True, current_query, [], 0, 0  # Reset for older articles
        else:
            # Recent articles work, continue with original query
            print(f"Entity availability good: {test_success}/{test_total} succeeded. Continuing with recent articles...\n")
            return False, query, articles_saved, test_success, test_fail
    
    return False, query, articles_saved, test_success, test_fail


def search_until_target_reached(query: str, target_count: int, batch_size: int,
                                 out_dir: str, email: str, processed_pmids: set,
                                 retstart: int, articles_saved: List[str]) -> List[str]:
    """Continue searching until target number of files with entities is reached.
    
    Args:
        query: PubMed search query (may be modified for older articles)
        target_count: Target number of files with entities
        batch_size: Batch size for API requests
        out_dir: Output directory for saved files
        email: Email for API identification
        processed_pmids: Set of already processed PMIDs
        retstart: Starting position for pagination
        articles_saved: List of PMIDs already saved with entities
        
    Returns:
        list: Updated list of saved article PMIDs
    """
    batch_fetch_size = 100
    max_attempts = target_count * 10  # Safety limit
    total_processed = len(processed_pmids)
    use_older_articles = "2021[PDAT]" in query or "2022[PDAT]" in query or "2023[PDAT]" in query
    
    while len(articles_saved) < target_count and total_processed < max_attempts:
        # Fetch next batch of PMIDs with pagination
        fetcher = PubMedFetcher(query=query, max_results=batch_fetch_size, email=email)
        pmids_batch = fetcher.fetch_pmids(retstart=retstart, retmax=batch_fetch_size)
        
        if not pmids_batch:
            # No more results from this query
            if not use_older_articles:
                # Switch to older articles query
                print(f"\nSwitching to older articles (2021-2023) to find more articles with entities...")
                # Extract base query (before any date filters)
                base_query = query
                if " AND " in query and ("[PDAT]" in query or "[pdat]" in query):
                    # Remove existing date filters
                    parts = query.split(" AND ")
                    base_query = " AND ".join([p for p in parts if "[PDAT]" not in p and "[pdat]" not in p])
                query = f"{base_query} AND (2023[PDAT] OR 2022[PDAT] OR 2021[PDAT])"
                use_older_articles = True
                retstart = 0
                processed_pmids.clear()  # Reset to allow new query
                continue
            else:
                print(f"\nNo more PMIDs found. Collected {len(articles_saved)}/{target_count} files with entities.")
                break
        
        # Filter out already processed PMIDs
        new_pmids = [pmid for pmid in pmids_batch if pmid not in processed_pmids]
        
        if not new_pmids:
            # All PMIDs in this batch were already processed, move to next page
            retstart += batch_fetch_size
            continue
        
        print(f"Processing {len(new_pmids)} PMIDs (progress: {len(articles_saved)}/{target_count} files with entities)...")
        
        # Process this batch
        for batch in chunked(new_pmids, batch_size):
            xml_text = fetcher.fetch_records(batch)
            articles = fetcher.parse_xml(xml_text)
            
            for art in articles:
                processed_pmids.add(art["pmid"])
                total_processed += 1
                
                save_article_txt(art, out_dir)
                success = append_entities_to_file(art["pmid"], out_dir)
                
                if success:
                    articles_saved.append(art["pmid"])
                    if len(articles_saved) % 10 == 0:
                        print(f"  Progress: {len(articles_saved)}/{target_count} files with entities saved")
                    
                    if len(articles_saved) >= target_count:
                        print(f"\n✓ Reached target: {len(articles_saved)}/{target_count} files with entities!")
                        return articles_saved
        
        if len(articles_saved) >= target_count:
            break
        
        # Move to next page
        retstart += len(new_pmids)
        
        # If we got fewer PMIDs than requested, we've reached the end of this query
        if len(pmids_batch) < batch_fetch_size:
            if not use_older_articles:
                # Switch to older articles query
                print(f"\nExpanding search to older articles (2021-2023)...")
                # Extract base query (before any date filters)
                base_query = query
                if " AND " in query and ("[PDAT]" in query or "[pdat]" in query):
                    # Remove existing date filters
                    parts = query.split(" AND ")
                    base_query = " AND ".join([p for p in parts if "[PDAT]" not in p and "[pdat]" not in p])
                query = f"{base_query} AND (2023[PDAT] OR 2022[PDAT] OR 2021[PDAT])"
                use_older_articles = True
                retstart = 0
                processed_pmids.clear()
            else:
                print(f"\nExhausted all available PMIDs. Found {len(articles_saved)}/{target_count} files with entities.")
                break
    
    return articles_saved


def fetch_with_entities(query: str, target_count: int, batch_size: int,
                        out_dir: str, email: str) -> List[str]:
    """Main function to fetch articles with entities until target count is reached.
    
    Args:
        query: PubMed search query
        target_count: Target number of files with entities
        batch_size: Batch size for API requests
        out_dir: Output directory for saved files
        email: Email for API identification
        
    Returns:
        list: List of PMIDs of saved articles with entities
    """
    print(f"Searching for articles with entities until {target_count} files are saved...")
    test_batch_size = 20
    
    # Test initial query for entity availability
    use_older_articles, current_query, articles_saved, success_count, failure_count = test_entity_availability(
        query, test_batch_size, batch_size, out_dir, email
    )
    
    processed_pmids = {pmid for pmid in articles_saved}
    retstart = len(articles_saved) if not use_older_articles else 0
    
    # Continue searching until target is reached
    articles_saved = search_until_target_reached(
        current_query, target_count, batch_size, out_dir, email,
        processed_pmids, retstart, articles_saved
    )
    
    if len(articles_saved) < target_count:
        print(f"\nWarning: Only found {len(articles_saved)}/{target_count} files with entities.")
        print("Consider expanding your query, using a different date range, or lowering --max-results.")
    
    return articles_saved
                          
