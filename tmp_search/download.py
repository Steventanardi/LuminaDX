import urllib.request
import urllib.parse
import json
import os
import re

dest_dir = r"d:\Steven Project\LuminaDx\Personal\Reference\Skin Cancer"
os.makedirs(dest_dir, exist_ok=True)

query = '(Melanoma OR "Skin Cancer" OR Dermatology) AND ("Large Language Model" OR "GPT-4" OR "ChatGPT" OR "Retrieval Augmented Generation") AND OPEN_ACCESS:y'
url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=" + urllib.parse.quote(query) + "&format=json&resultType=core&pageSize=10"

print("Searching Europe PMC for Open Access articles...")
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read().decode('utf-8'))
    
    results = data.get('resultList', {}).get('result', [])
    if not results:
        print("No open access results found.")
        exit(0)
        
    downloaded = 0
    for paper in results:
        if downloaded >= 4:
            break
            
        pmcid = paper.get('pmcid')
        title = paper.get('title', 'Unknown Title')
        
        if pmcid:
            print(f"Found: {title} (PMCID: {pmcid})")
            pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
            
            # Clean title for filename
            clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
            clean_title = clean_title[:100] # Limit length
            file_path = os.path.join(dest_dir, f"{clean_title}.pdf")
            
            print(f"Downloading PDF to {file_path}...")
            try:
                pdf_req = urllib.request.Request(pdf_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(pdf_req) as response, open(file_path, 'wb') as out_file:
                    out_file.write(response.read())
                print("Download complete.")
                downloaded += 1
            except Exception as e:
                print(f"Failed to download PDF: {e}")
        else:
            print(f"Skipping {title} - no PMCID available for direct PDF download.")
            
except Exception as e:
    print(f"Search failed: {e}")
