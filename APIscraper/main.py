"""Main orchestrator for PubMed article fetching with entity extraction."""

import argparse
import os
import textwrap

from pubmed_fetcher import PubMedFetcher, chunked, save_article_txt
from search_handler import fetch_with_entities
from statistics import get_entity_statistics, print_entity_statistics


def main():
    parser = argparse.ArgumentParser(
        description="Fetch PubMed title/abstracts via Entrez and save per-PMID .txt files."
    )
    parser.add_argument("--query", required=True, help="PubMed search query.")
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum PMIDs to fetch via esearch.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="PMIDs per efetch request (PubMed allows up to a few hundred).",
    )
    parser.add_argument(
        "--out-dir",
        default="data_raw",
        help="Directory to write <pmid>.txt files.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Contact email (recommended by NCBI for identification).",
    )
    parser.add_argument(
        "--no-entities",
        action="store_true",
        help="Skip fetching PubTator entity annotations.",
    )
    args = parser.parse_args()

    # Automatically skip entities and use data_simplified directory if generating more than 100 files for speed
    if args.max_results > 100:
        args.no_entities = True
        args.out_dir = "data_simplified"
        print(f"Note: Skipping entity annotations (only title/abstract) since --max-results={args.max_results} > 100")
        print(f"Note: Saving files to {args.out_dir} directory")

    # Ensure the output directory exists even if no articles are ultimately saved
    os.makedirs(args.out_dir, exist_ok=True)

    articles_saved = []
    target_count = args.max_results
    
    # Route to appropriate handler based on whether entities are required
    if not args.no_entities:
        # Use search handler to find articles with entities until target is reached
        articles_saved = fetch_with_entities(
            query=args.query,
            target_count=target_count,
            batch_size=args.batch_size,
            out_dir=args.out_dir,
            email=args.email
        )
    else:
        # No entities required - simple fetch
        fetcher = PubMedFetcher(
            query=args.query, max_results=args.max_results, email=args.email
        )
        pmids = fetcher.fetch_pmids()
        if not pmids:
            print("No PMIDs returned for that query.")
            return

        print(f"Fetched {len(pmids)} PMIDs. Downloading records in batches of {args.batch_size}...")
        
        for batch in chunked(pmids, args.batch_size):
            xml_text = fetcher.fetch_records(batch)
            articles = fetcher.parse_xml(xml_text)
            print(f"Parsed {len(articles)} articles in this batch.")
            for art in articles:
                save_article_txt(art, args.out_dir)
                articles_saved.append(art["pmid"])

    entity_note = "" if args.no_entities else " with PubTator entity annotations"
    saved_count = len(articles_saved)
    print(
        textwrap.dedent(
            f"""
            Done. Saved {saved_count} title/abstract files{entity_note} to: {args.out_dir}
            """
        ).strip()
    )
    
    # Print entity type statistics if entities were fetched
    if not args.no_entities and saved_count > 0:
        entity_stats = get_entity_statistics(args.out_dir)
        if entity_stats:
            print_entity_statistics(entity_stats, args.out_dir)


if __name__ == "__main__":
    main()
