from sri_dx.adapters.scraping import HttpxClient

def main():
    http = HttpxClient("sri-dx-acquisition/0.1")

    fr = http.get("https://example.com", timeout_s=20)
    print("URL FINAL:", fr.url)
    print("STATUS:", fr.status_code)
    print("MIME:", fr.mime_type)
    print("BYTES:", len(fr.content))

    assert fr.status_code < 400
    assert "text/html" in fr.mime_type
    assert len(fr.content) > 0
    print("OK step5 http")

if __name__ == "__main__":
    main()