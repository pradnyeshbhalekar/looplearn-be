import trafilatura

MIN_TEXT_LENGTH = 500

def scrape_article(url:str):
    try:
        downlaoded = trafilatura.fetch_url(url)
        if not downlaoded:
            return {"ok":False,"reason":"download_failed"}
        
        text = trafilatura.extract(downlaoded)
        if not text:
            return {"ok":False,"reasons":"extract_failed"}
        
        text.strip()

        if len(text) < MIN_TEXT_LENGTH:
            return {"ok":False,"reasons":"too short"}
        
        return {"ok":True,"text":text}
    
    except Exception as e:
        return {"ok":False,"error":str(e)}
    
