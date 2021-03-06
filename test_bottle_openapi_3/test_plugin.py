from webtest import TestApp


def test_basic_plugin_functionality(test_app: TestApp):
    resp = test_app.get("/foobar")
    assert resp.status_code == 200
    assert resp.json == {"foo": "bar"}

    resp = test_app.get("/baz", params={"qParam": 1})
    assert resp.status_code == 200
    assert resp.json == {"baz": True}

    resp = test_app.get("/baz", expect_errors=True)
    assert resp.status_code == 400
    assert isinstance(resp.json, dict)

    resp = test_app.post_json("/foobar", params={"test": "test"})
    assert resp.status_code == 201
    assert isinstance(resp.json, object)
    assert resp.json["one"] == 1.0