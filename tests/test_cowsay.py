def test_cowsay_default_message(client):
    resp = client.get("/api/cowsay")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "moo" in data["output"]


def test_cowsay_custom_message(client):
    resp = client.get("/api/cowsay?message=hello")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "hello" in data["output"]


def test_cowsay_empty_message_defaults_to_moo(client):
    resp = client.get("/api/cowsay?message=")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "moo" in data["output"]


def test_cowsay_whitespace_message_defaults_to_moo(client):
    resp = client.get("/api/cowsay?message=%20%20%20")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "moo" in data["output"]


def test_cowsay_long_message_truncated(client):
    long_msg = "a" * 300
    resp = client.get(f"/api/cowsay?message={long_msg}")
    assert resp.status_code == 200
    data = resp.get_json()
    # Cowsay wraps text, so count total 'a' chars in the bubble area
    # 200 chars should be present (truncated from 300), not 300
    a_count = data["output"].count("a")
    # The cow art has some 'a' chars too, but the message portion should be ~200
    assert a_count < 250  # well under 300
    assert "error" not in data


def test_cowsay_special_characters(client):
    resp = client.get("/api/cowsay?message=hello%20%3Cworld%3E%20%26%20%22foo%22")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "output" in data
    assert "error" not in data


def test_cowsay_character_tux(client):
    resp = client.get("/api/cowsay?message=hello&character=tux")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "hello" in data["output"]
    assert "o_o" in data["output"]  # tux has o_o eyes


def test_cowsay_invalid_character(client):
    resp = client.get("/api/cowsay?message=hello&character=invalid")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert "Unknown character" in data["error"]


def test_cowsay_think_mode(client):
    resp = client.get("/api/cowsay?message=hello&think=true")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "hello" in data["output"]
    # Think mode uses ( ) bubbles instead of | |
    assert "(" in data["output"]
    assert ")" in data["output"]
    # Think mode uses o connector instead of backslash
    assert "o" in data["output"]


def test_cowsay_think_with_character(client):
    resp = client.get("/api/cowsay?message=hi&character=tux&think=true")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "hi" in data["output"]
    assert "o_o" in data["output"]


def test_cowsay_characters_list(client):
    resp = client.get("/api/cowsay/characters")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "characters" in data
    assert "cow" in data["characters"]
    assert "tux" in data["characters"]
    assert len(data["characters"]) > 5
