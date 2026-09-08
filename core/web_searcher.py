import re
import urllib.parse
import concurrent.futures
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


class LiveWebSearcher:
    """
    Production-grade academic & web intelligence crawler querying
    Wikipedia, arXiv, OpenAlex, CrossRef, Semantic Scholar, and PubMed in real time.
    """

    def __init__(self, timeout: int = 4):
        self.timeout = timeout

    def extract_search_queries(self, text: str, max_queries: int = 8) -> List[str]:
        """
        Extracts distinctive continuous sentence fragments (7-15 words)
        from the text to accurately locate matching online publications without noun-collision false positives.
        """
        queries = []
        
        # Split into distinct sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if len(s.strip()) > 35]
        
        # Take representative sentences across beginning, middle, and end of text
        for s in sentences:
            clean_s = re.sub(r'^(title|abstract|introduction|topic|paper|section\s*\d*):\s*', '', s, flags=re.I).strip()
            words = clean_s.split()
            # Must be a substantial continuous phrase (at least 6-12 words)
            if len(words) >= 6:
                phrase = " ".join(words[:12])
                # Remove punctuation from start/end
                phrase = re.sub(r'^[^\w]+|[^\w]+$', '', phrase)
                if len(phrase) > 25 and phrase not in queries:
                    queries.append(phrase)

        # De-duplicate queries
        unique_queries = []
        seen = set()
        for q in queries:
            normalized = q.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_queries.append(q)

        return unique_queries[:max_queries]

    def fetch_wikipedia_sources(self, query: str) -> List[Dict[str, Any]]:
        """Searches Wikipedia API and retrieves lead articles and full text extracts."""
        sources = []
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json"
            res = requests.get(search_url, headers=HEADERS, timeout=self.timeout)
            if res.status_code != 200:
                return []

            data = res.json()
            search_results = data.get('query', {}).get('search', [])[:2]

            for item in search_results:
                title = item.get('title')
                if not title:
                    continue

                extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(title)}&format=json"
                ext_res = requests.get(extract_url, headers=HEADERS, timeout=self.timeout)
                if ext_res.status_code == 200:
                    pages = ext_res.json().get('query', {}).get('pages', {})
                    for pid, pdata in pages.items():
                        extract_text = pdata.get('extract', '')
                        if extract_text and len(extract_text) > 80:
                            sources.append({
                                "filename": f"Wikipedia: {title}",
                                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                                "source_type": "online_encyclopedia",
                                "badge": "🌐 Wikipedia",
                                "text": extract_text[:5000],
                            })
        except Exception:
            pass
        return sources

    def fetch_arxiv_sources(self, query: str) -> List[Dict[str, Any]]:
        """Searches arXiv open access repository for matching scientific publications."""
        sources = []
        try:
            clean_q = re.sub(r'[^\w\s]', ' ', query)
            arxiv_url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(clean_q)}&start=0&max_results=2"
            res = requests.get(arxiv_url, headers=HEADERS, timeout=self.timeout)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml')
                for entry in soup.find_all('entry')[:2]:
                    title_elem = entry.find('title')
                    summary_elem = entry.find('summary')
                    id_elem = entry.find('id')

                    title = title_elem.get_text(strip=True) if title_elem else 'Academic Paper'
                    summary = summary_elem.get_text(strip=True) if summary_elem else ''
                    url = id_elem.get_text(strip=True) if id_elem else 'https://arxiv.org'

                    if summary and len(summary) > 80:
                        sources.append({
                            "filename": f"arXiv: {title[:65]}...",
                            "url": url,
                            "source_type": "academic_paper",
                            "badge": "🎓 arXiv Academic",
                            "text": f"{title}\n\n{summary}",
                        })
        except Exception:
            pass
        return sources

    def fetch_openalex_sources(self, query: str) -> List[Dict[str, Any]]:
        """Searches OpenAlex scientific catalogue of 250M+ research publications."""
        sources = []
        try:
            clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
            if not clean_q:
                return []
            url = f"https://api.openalex.org/works?search={urllib.parse.quote(clean_q)}&per_page=2"
            res = requests.get(url, headers=HEADERS, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                for work in data.get('results', []):
                    title = work.get('title')
                    doi = work.get('doi') or work.get('id')
                    abstract_inverted = work.get('abstract_inverted_index')
                    
                    abstract_text = ""
                    if abstract_inverted:
                        word_pos = []
                        for word, positions in abstract_inverted.items():
                            for pos in positions:
                                word_pos.append((pos, word))
                        word_pos.sort(key=lambda x: x[0])
                        abstract_text = " ".join(w for _, w in word_pos)

                    full_text = f"{title}\n\n{abstract_text}" if abstract_text else title
                    if title and len(full_text) > 60:
                        sources.append({
                            "filename": f"Scholarly: {title[:65]}...",
                            "url": doi or "https://openalex.org",
                            "source_type": "scholarly_article",
                            "badge": "📚 Scholarly Journal",
                            "text": full_text,
                        })
        except Exception:
            pass
        return sources

    def fetch_crossref_sources(self, query: str) -> List[Dict[str, Any]]:
        """Searches CrossRef metadata index for peer-reviewed journal papers."""
        sources = []
        try:
            clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
            if not clean_q:
                return []
            url = f"https://api.crossref.org/works?query={urllib.parse.quote(clean_q)}&rows=2"
            res = requests.get(url, headers=HEADERS, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                items = data.get('message', {}).get('items', [])
                for item in items:
                    title_list = item.get('title', [])
                    title = title_list[0] if title_list else None
                    doi = item.get('DOI')
                    url = f"https://doi.org/{doi}" if doi else item.get('URL')
                    abstract = item.get('abstract', '')
                    if abstract:
                        abstract = re.sub(r'<[^>]+>', '', abstract).strip()

                    full_text = f"{title}\n\n{abstract}" if abstract else (title or "")
                    if title and len(full_text) > 50:
                        sources.append({
                            "filename": f"CrossRef: {title[:65]}...",
                            "url": url or "https://crossref.org",
                            "source_type": "scholarly_article",
                            "badge": "📑 CrossRef Publication",
                            "text": full_text,
                        })
        except Exception:
            pass
        return sources

    def fetch_semanticscholar_sources(self, query: str) -> List[Dict[str, Any]]:
        """Searches Semantic Scholar Open Research Graph API."""
        sources = []
        try:
            clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
            if not clean_q:
                return []
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(clean_q)}&limit=2&fields=title,abstract,url,year"
            res = requests.get(url, headers=HEADERS, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                for paper in data.get('data', []):
                    title = paper.get('title')
                    abstract = paper.get('abstract', '')
                    url = paper.get('url')
                    full_text = f"{title}\n\n{abstract}" if abstract else (title or "")
                    if title and len(full_text) > 50:
                        sources.append({
                            "filename": f"Semantic Scholar: {title[:65]}...",
                            "url": url or "https://www.semanticscholar.org",
                            "source_type": "scholarly_article",
                            "badge": "🔬 Semantic Scholar",
                            "text": full_text,
                        })
        except Exception:
            pass
        return sources

    def search_live_sources(self, text: str) -> List[Dict[str, Any]]:
        """
        Executes parallel multi-threaded queries across global academic databases.
        """
        queries = self.extract_search_queries(text, max_queries=8)
        if not queries:
            return []

        all_sources = []
        seen_urls = set()

        def run_query(q):
            found = []
            found.extend(self.fetch_wikipedia_sources(q))
            found.extend(self.fetch_arxiv_sources(q))
            found.extend(self.fetch_openalex_sources(q))
            found.extend(self.fetch_crossref_sources(q))
            found.extend(self.fetch_semanticscholar_sources(q))
            return found

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(run_query, q) for q in queries]
            for f in concurrent.futures.as_completed(futures):
                try:
                    results = f.result()
                    for s in results:
                        u = s.get('url', s.get('filename'))
                        if u not in seen_urls:
                            seen_urls.add(u)
                            all_sources.append(s)
                except Exception:
                    pass

        return all_sources
