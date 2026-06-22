import urllib.request
import json
import urllib.parse

query = '("Retrieval Augmented Generation" OR RAG OR "Large Language Model" OR ChatGPT OR GPT-4) AND (Melanoma OR Dermatology OR "Skin Cancer") AND ("2023"[Date - Publication] : "3000"[Date - Publication])'
url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=" + urllib.parse.quote(query) + "&retmode=json&retmax=10"

try:
    req = urllib.request.urlopen(url)
    res = json.loads(req.read())
    pmids = res['esearchresult']['idlist']
    
    if not pmids:
        print("No results found.")
        exit(0)
        
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=" + ",".join(pmids) + "&retmode=json"
    req_sum = urllib.request.urlopen(summary_url)
    res_sum = json.loads(req_sum.read())
    
    for pmid in pmids:
        title = res_sum['result'][pmid]['title']
        print(f"Title: {title}")
        print(f"URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        print("---")
except Exception as e:
    print(e)
