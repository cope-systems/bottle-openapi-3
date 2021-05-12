__version__ = (0, 1, 0)
__author__ = "Robert Cope (Cope Systems)"

from bottle import Request, Response, json_dumps, SimpleTemplate, static_file, request, response, HTTPResponse
from openapi_core.validation.request.datatypes import OpenAPIRequest, RequestParameters, RequestValidationResult
from openapi_core.validation.request.validators import RequestValidator
from openapi_core.validation.response.datatypes import OpenAPIResponse, ResponseValidationResult
from openapi_core.validation.response.validators import ResponseValidator
from openapi_core.validation.exceptions import InvalidSecurity
from openapi_core.schema.media_types.exceptions import InvalidContentType
from openapi_core.templating.paths.exceptions import OperationNotFound, PathNotFound
from openapi_core import create_spec
from openapi_spec_validator import validate_spec
from six.moves.urllib.parse import urljoin, urlparse
from functools import wraps
import logging
import re
import os


openapi_3_plugin_logger = logging.getLogger(__name__)

BOTTLE_PATH_PARAMETER_REGEX = re.compile(r'/<(.+?)(:.+)?>')

SWAGGER_UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
        'vendor', 'swagger-ui-3.38.0-dist')
SWAGGER_UI_INDEX_TEMPLATE_PATH = os.path.join(SWAGGER_UI_DIR, 'index.html.st')

with open(SWAGGER_UI_INDEX_TEMPLATE_PATH, 'r') as f:
    SWAGGER_UI_INDEX_TEMPLATE = f.read()


def _get_mimetype(content_type: str) -> str:
    return content_type.partition(";")[0]


def _render_index_html(spec_url, validator_url=None):
    return SimpleTemplate(SWAGGER_UI_INDEX_TEMPLATE).render(
        spec_url=spec_url,
        validator_url=json_dumps(validator_url)
    )


def _error_response(status, msg):
    response.status = status
    return {
        "status": "error",
        "message": msg
    }


def _validation_error_response(status, payload):
    response.status = status
    return {
        "status": "error",
        "errors": payload
    }


def _generate_request_parameters(req: Request) -> RequestParameters:
    return RequestParameters(
        path=req.url_args,
        query=req.query,
        header=dict(req.headers),
        cookie=dict(req.cookies)
    )


def _bottle_request_to_openapi_request(req: Request) -> OpenAPIRequest:
    # TODO: The default JSON deserializer for the OpenAPI toolkit does not handle
    # bytes I/O or streams, it looks like it requires strings. Can we bolt in an
    # alternate deserializer to make this work better?
    return OpenAPIRequest(
        full_url_pattern=BOTTLE_PATH_PARAMETER_REGEX.sub(r'/{\1}', req.route.rule),
        method=req.method.lower(),
        parameters=_generate_request_parameters(req),
        body=req.body.read(),
        mimetype=_get_mimetype(req.content_type)
    )


def _bottle_response_to_openapi_response(resp: Response) -> OpenAPIResponse:
    return OpenAPIResponse(
        data=resp.body,
        status_code=resp.status_code,
        mimetype=_get_mimetype(resp.content_type)
    )


def default_request_error_handler(req: Request, request_validation_result: RequestValidationResult):
    assert request_validation_result.errors, "Should have errors associated with the request validation."
    status = 400
    for error in request_validation_result.errors:
        if isinstance(error, InvalidSecurity):
            return _error_response(401, "Authentication Required!")
        if isinstance(error, OperationNotFound):
            status = 405
        if isinstance(error, PathNotFound):
            status = 404
        if isinstance(error, InvalidContentType):
            status = 415
    openapi_3_plugin_logger.warning(
        "Request validation failure. Request: {0} Validation Result: {1}"
        "".format(req, request_validation_result)
    )
    return _validation_error_response(status, [str(e) for e in request_validation_result.errors])


def default_response_error_handler(req: Request, resp: Response, response_validation_result: ResponseValidationResult):
    assert response_validation_result.errors, "Should have errors associated with the request validation."
    openapi_3_plugin_logger.error(
        "Response validation failure handling route! Request: {0}, Result: {1}"
        "".format(req, response_validation_result)
    )
    return _validation_error_response(500, [str(e) for e in response_validation_result.errors])


def default_server_error_handler(req: Request, e: Exception):
    openapi_3_plugin_logger.exception("Unhandled server exception caught running OpenAPI route handler.")
    return _error_response(500, repr(e))


class OpenAPIPlugin(object):
    DEFAULT_SWAGGER_SCHEMA_SUBURL = '/openapi.json'
    DEFAULT_SWAGGER_UI_SUBURL = '/ui/'

    name = 'openapi3'
    api = 2

    def __init__(self, openapi_def,
                 validate_openapi_spec=True,
                 validate_requests=True,
                 validate_responses=True,
                 auto_jsonify=True,
                 request_error_handler=default_request_error_handler,
                 response_error_handler=default_response_error_handler,
                 exception_handler=default_server_error_handler,
                 openapi_base_path=None,
                 adjust_api_base_path=True,
                 serve_openapi_schema=True,
                 openapi_schema_suburl=DEFAULT_SWAGGER_SCHEMA_SUBURL,
                 openapi_schema_route_name=None,
                 serve_swagger_ui=False,
                 swagger_ui_schema_url=None,
                 swagger_ui_suburl=DEFAULT_SWAGGER_UI_SUBURL,
                 swagger_ui_route_name=None,
                 swagger_ui_validator_url=None):
        """
        Create a new OpenAPI plugin for doing server-side validation in Bottle.

        :param openapi_def: A dictionary representation of the OpenAPI spec for this API.
        :type openapi_def: dict
        :param validate_openapi_spec: Should we validate the given OpenAPI specification when loading the plugin?
        :type validate_openapi_spec: bool
        :param validate_requests: Should we validate incoming requests against the given OpenAPI specification?
        :type validate_requests: bool
        :param validate_responses: Should we validate outgoing responses against the given OpenAPI specification?
        :type validate_responses: bool
        :param auto_jsonify: Should we automatically convert API responses from the results of the
            bottle routes into JSON?
        :type auto_jsonify: bool
        :param request_error_handler: An arity 2 callable that gets invoked when there is an
            error validating the request.
        :type request_error_handler: Callable
        :param response_error_handler: An arity 3 callable that gets invoked when there is an error
            validating the response.
        :type response_error_handler: Callable
        :param exception_handler: An arity 2 callable that gets invoked whenever there was an exception thrown
            in a route used to handle an API route defined in the specification.
        :type exception_handler: Callable
        :param openapi_base_path: The base suburl for all API routes defined in this spec. If adjust_api_base_path
           is true, this should override any settings in the specification.
        :type: Optional[str]
        :param adjust_api_base_path: Should we actually  alter the OpenAPI specification that's exposed to users to
           show the openapi_base_path that was set above?
        :type adjust_api_base_path: bool
        :param serve_openapi_schema: Should we serve the OpenAPI specification to our users?
        :type serve_openapi_schema: bool
        :param openapi_schema_suburl: The suburl path used to serve the OpenAPI specification.
        :type openapi_schema_suburl: str
        :param openapi_schema_route_name: The bottle route name for the OpenAPI specification.
        :type openapi_schema_route_name: Optional[str]
        :param serve_swagger_ui: Should we serve the embedded Swagger UI for API discovery?
        :type serve_swagger_ui: bool
        :param swagger_ui_schema_url: The URL for the OpenAPI spec to load in the Swagger UI.
        :type swagger_ui_schema_url: str
        :param swagger_ui_suburl: The suburl to serve the embedded Swagger UI under.
        :type swagger_ui_suburl: str
        :param swagger_ui_route_name: The bottle route name for the base page of the embedded Swagger UI.
        :type swagger_ui_route_name: Optional[str]
        :param swagger_ui_validator_url: The URL to a Swagger validator to use in the UI.
        """
        self.openapi_def = dict(openapi_def)
        if openapi_base_path is not None:
            self.openapi_def.update(basePath=openapi_base_path)

        if validate_openapi_spec:
            validate_spec(self.openapi_def)
        self.openapi_spec = create_spec(self.openapi_def)
        self.request_validator = RequestValidator(self.openapi_spec)
        self.response_validator = ResponseValidator(self.openapi_spec)
        self.validate_requests = validate_requests
        self.validate_responses = validate_responses
        self.auto_jsonify = auto_jsonify
        self.request_error_handler = request_error_handler
        self.response_error_handler = response_error_handler
        self.exception_handler = exception_handler
        self.serve_swagger_ui = serve_swagger_ui
        self.swagger_ui_schema_url = swagger_ui_schema_url
        self.serve_openapi_schema = serve_openapi_schema
        if not serve_openapi_schema and swagger_ui_schema_url is None and serve_swagger_ui:
            openapi_3_plugin_logger.warning(
                "Swagger UI enabled, but plugin instance has no configured swagger specification source!"
            )
            openapi_3_plugin_logger.warning(
                "Defaulting to an empty Swagger specification source for the UI, this is likely a misconfiguration!"
            )

        self.swagger_ui_validator_url = swagger_ui_validator_url
        self.openapi_schema_suburl = openapi_schema_suburl
        self.openapi_schema_route_name = openapi_schema_route_name
        self.swagger_ui_suburl = swagger_ui_suburl

        self.openapi_base_path = openapi_base_path or urlparse(self.openapi_spec.default_url).path or '/'
        self.adjust_api_base_path = adjust_api_base_path

        fixed_base_path = (self.openapi_base_path.rstrip("/")) + "/"
        self.openapi_schema_url = urljoin(fixed_base_path, self.openapi_schema_suburl.lstrip("/"))
        self.swagger_ui_base_url = urljoin(fixed_base_path, self.swagger_ui_suburl.lstrip("/"))
        self.swagger_ui_route_name = swagger_ui_route_name

    def setup(self, app):
        if self.serve_openapi_schema:
            @app.get(self.openapi_schema_url, name=self.openapi_schema_route_name)
            def swagger_schema():
                spec_dict = self.openapi_def
                if self.adjust_api_base_path and "basePath" in spec_dict:
                    spec_dict["basePath"] = urljoin(
                        urljoin("/", request.environ.get('SCRIPT_NAME', '').strip('/') + '/'),
                        self.openapi_base_path.lstrip("/")
                    )
                return spec_dict

        if self.serve_swagger_ui:
            @app.get(self.swagger_ui_base_url, name=self.swagger_ui_route_name)
            def swagger_ui_index():
                if self.swagger_ui_schema_url is not None and callable(self.swagger_ui_schema_url):
                    schema_url = self.swagger_ui_schema_url()
                elif self.swagger_ui_schema_url is not None:
                    schema_url = self.swagger_ui_schema_url
                elif self.serve_openapi_schema:
                    schema_url = app.get_url(self.openapi_schema_url)
                else:
                    schema_url = ""
                if self.swagger_ui_validator_url is not None and callable(self.swagger_ui_validator_url):
                    validator_url = self.swagger_ui_validator_url()
                else:
                    validator_url = self.swagger_ui_validator_url
                return _render_index_html(
                    schema_url,
                    validator_url=validator_url
                )

            @app.get(urljoin(self.swagger_ui_base_url, "<path:path>"))
            def swagger_ui_assets(path):
                return static_file(path, SWAGGER_UI_DIR)

    def apply(self, callback, route):
        @wraps(callback)
        def wrapper(*args, **kwargs):
            return self._validate_this(callback, route, *args, **kwargs)
        return wrapper

    def _validate_this(self, callback, route, *args, **kwargs):
        if not route.rule.startswith(self.openapi_base_path):
            return callback(*args, **kwargs)
        elif self.serve_openapi_schema and route.rule == self.openapi_schema_url:
            return callback(*args, **kwargs)
        elif self.serve_swagger_ui and route.rule.startswith(self.swagger_ui_base_url):
            return callback(*args, **kwargs)
        else:
            try:
                openapi_request = _bottle_request_to_openapi_request(request)
                if self.validate_requests:
                    request_validation_result = self.request_validator.validate(openapi_request)
                else:
                    request_validation_result = None
                if not self.validate_requests or not request_validation_result.errors:
                    request.openapi_request = openapi_request
                    result = callback(*args, **kwargs)
                    if self.auto_jsonify and isinstance(result, (dict, list)):
                        response.body = result = json_dumps(result)
                        response.content_type = 'application/json'
                        openapi_response = _bottle_response_to_openapi_response(response)
                    elif self.auto_jsonify and isinstance(result, HTTPResponse):
                        result.body = json_dumps(result.body)
                        response.content_type = result.content_type = 'application/json'
                        openapi_response = _bottle_response_to_openapi_response(result)
                    elif isinstance(result, HTTPResponse):
                        openapi_response = _bottle_response_to_openapi_response(result)
                    else:
                        response.body = result
                        openapi_response = _bottle_response_to_openapi_response(response)
                    if self.validate_responses:
                        response_validation_result = self.response_validator.validate(openapi_request, openapi_response)
                    else:
                        response_validation_result = None
                    if not self.validate_responses or not response_validation_result.errors:
                        return result
                    else:
                        return self.response_error_handler(
                            request,
                            result if isinstance(result, Response) else response,
                            response_validation_result
                        )
                else:
                    return self.request_error_handler(request, request_validation_result)
            except Exception as e:
                # Should we attempt to validate an HTTP response that was raised?
                if isinstance(e, HTTPResponse):
                    raise e
                return self.exception_handler(request, e)
            finally:
                request.openapi_request = None
