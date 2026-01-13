# Reference 2 - this script involves the use of Cursor AI https://cursor.com

"""
Lightweight PubMed API fetcher to produce the same basic text layout this
project consumes (per-PMID `.txt` with title/abstract rows). This does NOT
perform entity tagging or relation extraction; it only pulls title/abstracts.

Usage (example):
    python scripts/pubmed_fetcher.py --query "lung cancer" --max-results 200 --out-dir data_raw

Outputs:
    data_raw/<PMID>.txt with:
        PMID|t|<title>
        PMID|a|<abstract>
"""

import argparse
import os
import textwrap
import xml.etree.ElementTree as ET
from typing import Iterable, List, Dict

import requests


class PubMedFetcher:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self, query: str, max_results: int = 100, email: str | None = None):
        self.query = query
        self.max_results = max_results
        self.email = email

    def fetch_pmids(self, retstart: int = 0, retmax: int = None) -> List[str]:
        """Call esearch to get a list of PMIDs for the query.
        
        Args:
            retstart: Starting position for pagination (0-indexed)
            retmax: Maximum number of results to return (uses self.max_results if None)
        """
        if retmax is None:
            retmax = self.max_results
        params = {
            "db": "pubmed",
            "term": self.query,
            "retstart": retstart,
            "retmax": retmax,
            "usehistory": "y",
            "retmode": "json",
        }
        if self.email:
            params["email"] = self.email
        resp = requests.get(f"{self.BASE_URL}esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        return pmids

    def fetch_records(self, pmids: Iterable[str]) -> str:
        """Call efetch to retrieve XML for a batch of PMIDs."""
        pmid_str = ",".join(pmids)
        params = {
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "xml",
            "rettype": "abstract",
        }
        if self.email:
            params["email"] = self.email
        resp = requests.get(f"{self.BASE_URL}efetch.fcgi", params=params, timeout=60)
        resp.raise_for_status()
        return resp.text

    def parse_xml(self, xml_text: str) -> List[Dict[str, str]]:
        """Extract PMID, Title, AbstractText from efetch XML."""
        root = ET.fromstring(xml_text)
        articles: List[Dict[str, str]] = []
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            # AbstractText can appear multiple times; join if needed
            abstract_parts = [
                a.text or "" for a in article.findall(".//Abstract/AbstractText")
            ]
            abstract = " ".join(abstract_parts).strip()
            if pmid_el is None or title_el is None:
                continue
            articles.append(
                {
                    "pmid": pmid_el.text.strip(),
                    "title": (title_el.text or "").strip(),
                    "abstract": abstract,
                }
            )
        return articles


def save_article_txt(article: Dict[str, str], out_dir: str) -> None:
    """Write a single article to <out_dir>/<pmid>.txt in the repo's expected format.
    
    Only creates the file if both title and abstract are present and non-empty.
    """
    pmid = article["pmid"]
    title = article["title"].replace("\n", " ").strip()
    abstract = article["abstract"].replace("\n", " ").strip()
    
    # Only save if both title and abstract exist
    if not title or not abstract:
        print(f"Skipped {pmid}: missing {'title' if not title else 'abstract'}")
        return
    
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{pmid}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{pmid}|t|{title}\n")
        f.write(f"{pmid}|a|{abstract}\n")
    print(f"Wrote {path}")


def chunked(iterable: List[str], size: int) -> Iterable[List[str]]:
    """Yield fixed-size chunks from a list."""
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]

# end of reference
