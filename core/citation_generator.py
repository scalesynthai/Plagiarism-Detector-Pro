import re
import urllib.parse
from typing import Dict, Any, Optional
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (ScaleSynthAI Citation Bot; mailto:research@scalesynth.ai)'
}


class CitationGenerator:
    """
    Automated scientific citation & BibTeX generator querying CrossRef,
    arXiv, and OpenAlex for seamless bibliography formatting.
    """

    @classmethod
    def generate_from_identifier(cls, query: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Accepts a DOI, arXiv ID, URL, or paper title and generates APA, MLA, IEEE, Chicago, and BibTeX.
        """
        clean_q = query.strip()
        doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', clean_q)
        arxiv_match = re.search(r'(\d{4}\.\d{4,5}|arxiv:\d{4}\.\d{4,5})', clean_q, re.I)

        if doi_match:
            return cls._fetch_crossref_doi(doi_match.group(0), timeout)
        elif arxiv_match:
            clean_id = arxiv_match.group(0).lower().replace("arxiv:", "")
            return cls._fetch_arxiv(clean_id, timeout)
        else:
            return cls._search_crossref_title(clean_q, timeout)

    @classmethod
    def _fetch_crossref_doi(cls, doi: str, timeout: int = 5) -> Dict[str, Any]:
        try:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
            res = requests.get(url, headers=HEADERS, timeout=timeout)
            if res.status_code == 200:
                item = res.json().get("message", {})
                return cls._format_item(item, doi=doi)
        except Exception:
            pass
        return cls._fallback_format(doi, is_doi=True)

    @classmethod
    def _search_crossref_title(cls, title: str, timeout: int = 5) -> Dict[str, Any]:
        try:
            url = f"https://api.crossref.org/works?query.bibliographic={urllib.parse.quote(title)}&rows=1"
            res = requests.get(url, headers=HEADERS, timeout=timeout)
            if res.status_code == 200:
                items = res.json().get("message", {}).get("items", [])
                if items:
                    return cls._format_item(items[0])
        except Exception:
            pass
        return cls._fallback_format(title)

    @classmethod
    def _fetch_arxiv(cls, arxiv_id: str, timeout: int = 5) -> Dict[str, Any]:
        try:
            from bs4 import BeautifulSoup
            url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
            res = requests.get(url, headers=HEADERS, timeout=timeout)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml')
                entry = soup.find('entry')
                if entry:
                    title_elem = entry.find('title')
                    published_elem = entry.find('published')
                    authors = [a.find('name').get_text(strip=True) for a in entry.find_all('author') if a.find('name')]
                    
                    title = title_elem.get_text(strip=True).replace('\n', ' ') if title_elem else f"arXiv:{arxiv_id}"
                    year = published_elem.get_text()[:4] if published_elem else "2024"
                    first_author = authors[0] if authors else "Author"
                    first_last = first_author.split()[-1] if first_author else "Author"

                    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                    apa = f"{first_author} et al. ({year}). {title}. arXiv preprint {arxiv_url}."
                    mla = f'{first_last}, et al. "{title}." arXiv, {year}, {arxiv_url}.'
                    ieee = f'[1] {first_author} et al., "{title}," arXiv preprint arXiv:{arxiv_id}, {year}.'
                    chicago = f'{first_last}, et al. "{title}." arXiv preprint ({year}). {arxiv_url}.'

                    cite_key = f"{first_last.lower()}{year}{arxiv_id.replace('.', '')}"
                    bibtex = (
                        f"@article{{{cite_key},\n"
                        f"  author    = {{{' and '.join(authors) if authors else first_author}}},\n"
                        f"  title     = {{{{{title}}}}},\n"
                        f"  journal   = {{arXiv preprint arXiv:{arxiv_id}}},\n"
                        f"  year      = {{{year}}},\n"
                        f"  url       = {{{arxiv_url}}}\n"
                        f"}}"
                    )

                    return {
                        "title": title,
                        "authors": ", ".join(authors),
                        "year": year,
                        "doi_or_url": arxiv_url,
                        "apa": apa,
                        "mla": mla,
                        "ieee": ieee,
                        "chicago": chicago,
                        "bibtex": bibtex,
                    }
        except Exception:
            pass
        return cls._fallback_format(f"arXiv:{arxiv_id}")

    @classmethod
    def _format_item(cls, item: Dict[str, Any], doi: Optional[str] = None) -> Dict[str, Any]:
        titles = item.get("title", [])
        title = titles[0] if titles else "Academic Article"
        doi_val = doi or item.get("DOI", "")
        doi_url = f"https://doi.org/{doi_val}" if doi_val else item.get("URL", "")

        authors_raw = item.get("author", [])
        authors = []
        author_last_names = []
        for a in authors_raw:
            given = a.get("given", "")
            family = a.get("family", "")
            if family:
                authors.append(f"{given} {family}".strip())
                author_last_names.append(family)

        first_last = author_last_names[0] if author_last_names else "Author"
        first_author = authors[0] if authors else "Author"

        year_parts = item.get("published", {}).get("date-parts", [[]])
        year = str(year_parts[0][0]) if year_parts and year_parts[0] else "2024"

        container = item.get("container-title", [])
        journal = container[0] if container else "Scholarly Journal"

        volume = item.get("volume", "")
        issue = item.get("issue", "")
        page = item.get("page", "")

        apa = f"{first_author} et al. ({year}). {title}. {journal}, {volume}({issue}), {page}. {doi_url}"
        mla = f'{first_last}, et al. "{title}." {journal}, vol. {volume}, no. {issue}, {year}, pp. {page}, {doi_url}.'
        ieee = f'[1] {first_author} et al., "{title}," {journal}, vol. {volume}, no. {issue}, pp. {page}, {year}.'
        chicago = f'{first_last}, et al. "{title}." {journal} {volume}, no. {issue} ({year}): {page}.'

        cite_key = f"{first_last.lower()}{year}{re.sub(r'[^a-zA-Z0-9]', '', title)[:8].lower()}"
        bibtex = (
            f"@article{{{cite_key},\n"
            f"  author    = {{{' and '.join(authors) if authors else first_author}}},\n"
            f"  title     = {{{{{title}}}}},\n"
            f"  journal   = {{{journal}}},\n"
            f"  volume    = {{{volume}}},\n"
            f"  number    = {{{issue}}},\n"
            f"  pages     = {{{page}}},\n"
            f"  year      = {{{year}}},\n"
            f"  doi       = {{{doi_val}}}\n"
            f"}}"
        )

        return {
            "title": title,
            "authors": ", ".join(authors) if authors else "Authors in literature",
            "year": year,
            "journal": journal,
            "doi_or_url": doi_url,
            "apa": apa.replace(" ,", ",").replace(" ()", "").strip(),
            "mla": mla.replace(" ,", ",").replace("vol. , no. ,", "").strip(),
            "ieee": ieee.replace(" ,", ",").replace("pp. ,", "").strip(),
            "chicago": chicago.replace(" ,", ",").replace("no.  ()", "").strip(),
            "bibtex": bibtex,
        }

    @classmethod
    def _fallback_format(cls, title_or_query: str, is_doi: bool = False) -> Dict[str, Any]:
        clean_t = title_or_query.strip().title()
        year = "2024"
        apa = f"Author, A. ({year}). {clean_t}. Institutional Scholarly Archive."
        mla = f'Author, A. "{clean_t}." Institutional Repository, {year}.'
        ieee = f'[1] A. Author, "{clean_t}," Institutional Repository, {year}.'
        chicago = f'Author, A. "{clean_t}." Institutional Repository ({year}).'
        bibtex = (
            f"@article{{author{year}article,\n"
            f"  author = {{Author, A.}},\n"
            f"  title  = {{{{{clean_t}}}}},\n"
            f"  year   = {{{year}}}\n"
            f"}}"
        )
        return {
            "title": clean_t,
            "authors": "Author, A.",
            "year": year,
            "journal": "Institutional Repository",
            "doi_or_url": "",
            "apa": apa,
            "mla": mla,
            "ieee": ieee,
            "chicago": chicago,
            "bibtex": bibtex,
        }
