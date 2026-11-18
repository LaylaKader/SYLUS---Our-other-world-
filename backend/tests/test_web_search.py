from app.web_search import _safe_url, classify_search_request


def test_image_search_intent():
    assert classify_search_request("Can you show me pictures of Sylus?")[0] == "image"


def test_visual_description_question_triggers_images():
    assert classify_search_request("What does Sylus look like?")[0] == "image"


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


def test_search_followups_reuse_previous_results():
    from app.web_search import is_search_followup
    assert is_search_followup("Yeah, show me!")
    assert is_search_followup("Send me the image")
    assert is_search_followup("where is it?")
    assert not is_search_followup("Find me another meme")


def test_meme_query_removes_find_me_prefix():
    assert classify_search_request("Find me a funny meme") == ("image", "a funny meme")


def test_result_parser_extracts_search_links():
    from app.web_search import _ResultAnchors
    parser = _ResultAnchors()
    parser.feed('<a class="result__a" href="https://example.com/page">Example page</a>')
    assert parser.items == [{"href": "https://example.com/page", "text": "Example page"}]


def test_music_link_request_is_classified_and_cleaned():
    assert classify_search_request("Then give me a link of a nice music") == ("music", "music")


def test_music_preference_followup_uses_prior_search_intent():
    from app.web_search import classify_search_request_with_history
    history = [
        {"role": "user", "body": "Then give me a link of a nice music"},
        {"role": "assistant", "body": "Looking for something specific?"},
    ]
    assert classify_search_request_with_history(
        "Something that you think fits me", history
    ) == ("music", "beautiful atmospheric romantic music recommendations")


def test_waiting_is_a_search_followup():
    from app.web_search import is_search_followup
    assert is_search_followup("I'm waiting~")


def test_ordinary_music_chat_does_not_trigger_search():
    assert classify_search_request("I love music.") is None
