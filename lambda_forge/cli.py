import os
import click

from lambda_forge.builders.authorizer_builder import AuthorizerBuilder
from lambda_forge.builders.docs_builder import DocsBuilder
from lambda_forge.builders.function_builder import FunctionBuilder
from lambda_forge.builders.layer_builder import LayerBuilder
from lambda_forge.builders.project_builder import ProjectBuilder
from lambda_forge.builders.service_builder import ServiceBuilder
from lambda_forge import layers, live_cli
from lambda_forge.logs import Logger
import pyfiglet

logger = Logger()

@click.group()
def forge():
    """
    Forge CLI tool for structuring and deploying AWS Lambda projects.

    This command group provides a suite of tools for building and managing AWS Lambda
    projects, including creating projects, functions, authorizers, services, and layers.
    """
    pass


@forge.command()
@click.argument("name")
@click.option("--repo-owner", help="Owner of the repository", required=True)
@click.option("--repo-name", help="Repository name", required=True)
@click.option(
    "--no-dev", help="Do not create a dev environment", is_flag=True, default=False
)
@click.option(
    "--no-staging",
    help="Do not create a staging environment",
    is_flag=True,
    default=False,
)
@click.option(
    "--no-prod", help="Do not create a prod environment", is_flag=True, default=False
)
@click.option(
    "--no-docs",
    help="Do not create documentation for the api endpoints",
    is_flag=True,
    default=False,
)
@click.option(
    "--region",
    help="AWS region to deploy the project",
    default="us-east-2",
)
@click.option(
    "--bucket",
    help="Bucket used to store the documentation",
    default="",
)
@click.option(
    "--coverage",
    help="Minimum coverage percentage",
    default=80,
)
def project(
    name,
    repo_owner,
    repo_name,
    no_dev,
    no_staging,
    no_prod,
    no_docs,
    region,
    bucket,
    coverage,
):
    """
    Initializes a new AWS Lambda project with a specified structure.

    This command sets up the initial project structure, including development, staging,
    and production environments, API documentation, and AWS deployment configurations.

    Requires specifying a S3 bucket if API documentation is enabled.
    """

    if no_docs is False and not bucket:
        raise click.UsageError(
            "You must provide a S3 bucket for the docs or use the flag --no-docs"
        )

    create_project(
        name,
        repo_owner,
        repo_name,
        no_dev,
        no_staging,
        no_prod,
        no_docs,
        region,
        bucket,
        coverage,
    )


def create_project(
    name,
    repo_owner,
    repo_name,
    no_dev,
    no_staging,
    no_prod,
    no_docs,
    region,
    bucket,
    coverage,
):

    project_builder = ProjectBuilder.a_project(name, not no_docs)

    if no_dev is False:
        project_builder = project_builder.with_dev()

    if no_staging is False:
        project_builder = project_builder.with_staging()

    if no_prod is False:
        project_builder = project_builder.with_prod()

    project_builder = (
        project_builder.with_app()
        .with_cdk(repo_owner, repo_name, region, bucket, coverage)
        .with_gitignore()
        .with_pytest_ini()
        .with_coveragerc()
        .with_requirements()
        .with_deploy_stage()
        .build()
    )

    if not no_docs:
        DocsBuilder.a_doc().with_config().with_lambda_stack().build()


@forge.command()
@click.argument("name")
@click.option("--description", required=True, help="Description for the endpoint")
@click.option(
    "--method", required=False, help="HTTP method for the endpoint", default="GET"
)
@click.option("--belongs-to", help="Folder name you want to share code accross lambdas")
@click.option("--endpoint", help="Endpoint for the API Gateway")
@click.option("--no-api", help="Do not create an API Gateway endpoint", is_flag=True)
@click.option(
    "--websocket", help="Function is going to be used for websockets", is_flag=True
)
@click.option(
    "--no-tests",
    help="Do not create unit tests and integration tests files",
    is_flag=True,
    default=False,
)
@click.option(
    "--public",
    help="Endpoint is public",
    is_flag=True,
    default=False,
)
def function(
    name, description, method, belongs_to, endpoint, no_api, websocket, no_tests, public
):
    """
    Creates a Lambda function with a predefined structure and API Gateway integration.

    Sets up a new Lambda function, including configuration files, unit tests, and
    optionally an API Gateway endpoint.

    An HTTP method must be provided if an API Gateway endpoint is not skipped.
    """
    method = method.upper() if method else None
    create_function(
        name,
        description,
        method,
        belongs_to,
        endpoint,
        no_api,
        websocket,
        no_tests,
        public,
    )


def create_function(
    name,
    description,
    http_method=None,
    belongs=None,
    endpoint=None,
    no_api=False,
    websocket=False,
    no_tests=False,
    public=False,
):

    function_builder = FunctionBuilder.a_function(name, description).with_config(
        belongs
    )

    if no_api is True:
        function_builder = function_builder.with_main()
        if no_tests is False:
            function_builder = function_builder.with_unit()

    elif websocket is True:
        function_builder = function_builder.with_websocket().with_main()
        if no_tests is False:
            function_builder = function_builder.with_unit()

    else:
        endpoint = endpoint or belongs or name
        if no_tests is True:
            function_builder = (
                function_builder.with_endpoint(endpoint)
                .with_api(http_method, public)
                .with_main()
            )
        else:
            function_builder = (
                function_builder.with_endpoint(endpoint)
                .with_api(http_method, public)
                .with_integration(http_method)
                .with_unit()
                .with_main()
            )

    function_builder.with_lambda_stack().build()


@forge.command()
@click.argument("name")
@click.option("--description", required=True, help="Description for the endpoint")
@click.option(
    "--default",
    help="Mark the authorizer as the default for all private endpoints with no authorizer set.",
    is_flag=True,
    default=False,
)
@click.option(
    "--no-tests",
    help="Do not create unit tests and integration tests files",
    is_flag=True,
    default=False,
)
def authorizer(name, description, default, no_tests):
    """
    Generates an authorizer for AWS Lambda functions.

    Creates an authorizer Lambda function, including configuration and deployment setup,
    to control access to other Lambda functions.

    The authorizer can be marked as the default for all private endpoints lacking a specific authorizer.
    """
    create_authorizer(name, description, default, no_tests)


def create_authorizer(name, description, default, no_tests):
    authorizer_builder = (
        AuthorizerBuilder.an_authorizer(name, description, "authorizers")
        .with_config(default)
        .with_main()
        .with_lambda_stack()
    )

    if no_tests is False:
        authorizer_builder = authorizer_builder.with_unit()

    authorizer_builder.build()


AVALABLE_SERVICES = sorted(
    [
        "sns",
        "dynamo_db",
        "s3",
        "event_bridge",
        "sqs",
        "secrets_manager",
        "cognito",
        "kms",
        "websockets",
    ]
)


@forge.command()
@click.argument(
    "service",
    type=click.Choice(AVALABLE_SERVICES),
)
def service(service):
    """
    Scaffolds the structure for a specified AWS service integration.

    Creates boilerplate code and configuration for integrating with AWS services like
    SNS, DynamoDB, S3, etc., within the Lambda project.

    The 'service' parameter is limited to a predefined list of supported AWS services.
    """
    create_service(service)


def create_service(service):
    service_builder = ServiceBuilder.a_service()

    services = {
        "sns": service_builder.with_sns,
        "dynamo_db": service_builder.with_dynamodb,
        "s3": service_builder.with_s3,
        "event_bridge": service_builder.with_event_bridge,
        "sqs": service_builder.with_sqs,
        "secrets_manager": service_builder.with_secrets_manager,
        "cognito": service_builder.with_cognito,
        "kms": service_builder.with_kms,
        "websockets": service_builder.with_websockets,
    }
    service_builder = services[service]()

    service_builder.build()


@forge.command()
@click.option(
    "--custom",
    help="Name of the custom layer to create",
)
@click.option(
    "--description",
    help="Layer description",
)
@click.option(
    "--install",
    help="Install all custom layers locally",
    is_flag=True,
)
def layer(custom, description, install):
    """
    Creates and installs a new Lambda layer.

    Sets up a new directory for the Lambda layer, prepares it for use with AWS Lambda,
    and updates the project's requirements.txt to include the new layer.

    This command facilitates layer management within the Lambda project structure.
    """
    create_layer(custom, description, install)


def create_layer(name, description, install):
    layer_builder = LayerBuilder.a_layer().with_layers()
    if name:
        layer_builder.with_custom_layers(name, description)
        layers.create_and_install_package(name)

    layer_builder.build()

    if install:
        layers.install_all_layers()


@forge.command()
@click.argument("function_name")
@click.option(
    "--timeout",
    help="Timeout in seconds for the function",
    default=30,
)
def live(function_name, timeout):
    create_live_dev(function_name, timeout)


def create_live_dev(function_name, timeout):
    text = "Live Development"
    ascii_art = pyfiglet.figlet_format(text, width=200)
    logger.log(ascii_art, "green", 1)
    live_cli.run_live(function_name, timeout)



if __name__ == "__main__":
    forge()
