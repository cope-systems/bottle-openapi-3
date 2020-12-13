import pytest
from webtest import TestApp
from bottle import Bottle, request

from bottle_openapi_3 import OpenAPIPlugin


@pytest.fixture
def openapi3_paths():
    return {
        "/foobar": {
            "get": {
                "summary": "Get something.",
                "responses": {
                    "200": {
                        "description": "Return an object",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/baz": {
            "get": {
                "summary": "???",
                "parameters": [
                    {
                        "name": "qParam",
                        "in": "query",
                        "schema": {
                            "type": "integer"
                        },
                        "required": True
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Return an object",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def openapi3_spec(openapi3_paths):
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "description": "API for running tests",
            "version": "0.0.1"
        },
        "paths": openapi3_paths
    }


@pytest.fixture
def openapi_plugin(openapi3_spec):
    return OpenAPIPlugin(
        openapi3_spec
    )


@pytest.fixture
def bottle_app():
    app = Bottle()

    @app.route("/foobar")
    def foobar_handler():
        return {"foo": "bar"}

    @app.route("/baz")
    def baz_handler():
        assert "qParam" in request.params
        assert request.params["qParam"].isdigit()
        return {"baz": True}
    return app


@pytest.fixture
def test_app(bottle_app, openapi_plugin):
    bottle_app.install(openapi_plugin)
    return TestApp(bottle_app)
