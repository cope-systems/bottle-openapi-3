import pytest
from webtest import TestApp
from bottle import Bottle, request, response

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
            },
            "post": {
                "summary": "Create something",
                "requestBody": {
                    "description": "Input data",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Thing created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/FooObject"
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
def openapi3_components():
    return {
        "schemas": {
            "FooObject": {
                "type": "object",
                "properties": {
                    "one": {
                        "type": "number"
                    },
                    "two": {
                        "type": "string"
                    },
                    "three": {
                        "type": "object"
                    }
                },
                "required": ["one", "two"]
            }
        }
    }

@pytest.fixture
def openapi3_spec(openapi3_paths, openapi3_components):
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "description": "API for running tests",
            "version": "0.0.1"
        },
        "paths": openapi3_paths,
        "components": openapi3_components
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

    @app.route("/foobar", method="POST")
    def foobar_post_handler():
        import logging
        logging.warning("???")
        response.status = 201
        logging.warning("{0}".format(request.openapi_request))
        return {
            "one": 1.0,
            "two": "???",
            "three": {
                "foo": "bar"
            }
        }

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
