==========================
Bottle OpenAPI 3 Plugin
==========================
--------------------------
About
--------------------------

The Bottle OpenAPI 3 Plugin is a toolkit for performing validation of requests
against an OpenAPI document for `Bottle <https://bottlepy.org/docs/0.12/>`_ applications. It is built on the `openapi-core <https://github.com/p1c2u/openapi-core>`_
and `openapi-spec-validator <https://github.com/p1c2u/openapi-spec-validator>`_ libraries, and supports
the `OpenAPI 3 specification <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md>`_.

--------
License
--------

This codebase is MIT licensed.

--------------------------
Requirements
--------------------------

A relatively recent version of Python (3.5+) is required. This plugin depends on the
aforementioned ``openapi-core`` and ``openapi-spec-validator`` libraries, and also requires
a relatively recent version of ``bottle`` (0.12+).


--------------------------
Quickstart
--------------------------

The Bottle OpenAPI 3 plugin may either be installed from `pypi <https://pypi.org/project/bottle-openapi-3/>`_  as the ``bottle-openapi-3`` package:

    pip install bottle-openapi-3

or may be installed from source from the `git repository <https://github.com/cope-systems/bottle-openapi-3>`_:

    python setup.py install

Once the plugin is installed, it may be used in a Bottle application by loading the OpenAPI schema and installing the
plugin. An example:

.. code-block:: python

    import bottle
    import yaml
    from bottle_openapi_3 import OpenAPIPlugin

    app = bottle.Bottle()

    with open("swagger.yaml") as f:
        spec = yaml.load(f)

    @app.route("/api/foo")
    def foo_handler():
        return {"foo": "bar"}

    app.install(OpenAPIPlugin(spec))

    app.run()

The example's specification:

.. code-block:: yaml

    openapi: 3.0.0
    info:
      title: My API
    servers:
      - url: /api
    paths:
      /foo:
        get:
           summary: Fetch an object
           responses:
             "200":
                description: "An object was successfully generated."
                content:
                  application/json:
                    schema: {"type": "object"}


--------------------------
Advanced Usage
--------------------------

TODO



--------------------------
Changelog
--------------------------

0.1.2 (May 2021)
*****************

Fixed an issue decoding the request body for HTTP methods like
POST, PUT, etc.


0.1.0 (Jan 2021)
*****************

Initial alpha release of the OpenAPI 3 plugin for
Bottle. Most functionality should be implemented.