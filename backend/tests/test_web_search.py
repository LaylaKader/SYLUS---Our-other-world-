from app.web_search import _safe_url, classify_search_request


def test_image_search_intent():
    assert classify_search_request("Can you show me pictures of Sylus?")[0] == "image"


def test_meme_search_intent():
    assert classify_search_request("Find me a meme about being sleepy") [0] == "image"


def test_video_search_intent():
    assert classify_search_request("Find me YouTube videos of Sylus") [0] == "video"


def test_link_search_intent():
    assert classify_search_request("Send me links to the official website") [0] == "link"


def test_normal_chat_does_not_trigger_search():
    assert classify_search_request("I missed you today.") is None


def test_only_public_https_urls_are_renderable():
    assert _safe_url("https://example.com/image.jpg") == "https://example.com/image.jpg"
    assert _safe_url("http://example.com/image.jpg") == ""
    assert _safe_url("https://127.0.0.1/private") == ""
    assert _safe_url("file:///etc/passwd") == ""
