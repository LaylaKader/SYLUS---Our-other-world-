from app.image_delivery import extract_image_directive, extract_link_directive, should_generate_image


def test_extracts_private_image_directive_without_showing_it():
    text = "There. [[SYLUS_IMAGE: cinematic portrait of Sylus in a black coat]]"
    clean, prompt = extract_image_directive(text)
    assert clean == "There."
    assert prompt == "cinematic portrait of Sylus in a black coat"


def test_no_directive_keeps_normal_reply():
    assert extract_image_directive("I missed you.") == ("I missed you.", None)


def test_direct_image_requests_trigger_generation():
    assert should_generate_image("Send me an image of you.")
    assert should_generate_image("Can you draw us together?")
    assert should_generate_image("Send me the image")


def test_image_discussion_does_not_trigger_generation():
    assert not should_generate_image("What do you think of this image?")
    assert not should_generate_image("I found a picture online.")
    assert not should_generate_image("I missed you today.")

def test_web_image_search_is_not_mistaken_for_generation():
    assert not should_generate_image("Show me pictures of Sylus.")
    assert not should_generate_image("Find me a funny meme.")


def test_extracts_private_link_directive_without_showing_it():
    clean, query = extract_link_directive("This one suits you. [[SYLUS_LINK: atmospheric romantic songs]]")
    assert clean == "This one suits you."
    assert query == "atmospheric romantic songs"


def test_no_link_directive_keeps_normal_reply():
    assert extract_link_directive("I found something for you.") == ("I found something for you.", None)
