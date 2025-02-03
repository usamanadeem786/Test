import secrets

import typer

from auth.crypto.encryption import generate_key
from auth.services.password import PasswordValidation


def add_commands(app: typer.Typer) -> typer.Typer:
    @app.command()
    def quickstart(
        user_email: str = typer.Option(..., prompt=True, help="The admin user email"),
        user_password: str = typer.Option(
            ...,
            prompt=True,
            confirmation_prompt=True,
            hide_input=True,
            help="The admin user password",
        ),
        docker: bool = typer.Option(
            False,
            help="Show the Docker command to run the Auth server with required environment variables.",
        ),
        port: int = typer.Option(
            8000, help="Port on which you want to expose the Auth server."
        ),
        host: str = typer.Option(
            "localhost", help="Host on which you want to expose the Auth server."
        ),
        ssl: bool = typer.Option(
            False,
            help="Whether the Auth server will be served over SSL. For local development, it'll likely be false.",
        ),
    ):
        """Generate secrets and environment variables to help users getting started quickly."""

        password_validation = PasswordValidation.validate(
            user_password, min_length=8, min_score=3
        )
        if not password_validation.valid:
            typer.secho(
                "Sorry, your password does not meet our complexity requirements. Please re-run with a more complex password.",
                fg=typer.colors.RED,
            )
            for message in password_validation.messages:
                print(f"Error message: {message}")
            raise typer.Exit(code=1)

        typer.secho(
            "⚠️  Be sure to save the generated secrets somewhere safe for subsequent runs. Otherwise, you may lose access to the data.",
            bold=True,
            fg="red",
            err=True,
        )
        environment_variables = {
            "SECRET": secrets.token_urlsafe(64),
            "AUTH_CLIENT_ID": secrets.token_urlsafe(),
            "AUTH_CLIENT_SECRET": secrets.token_urlsafe(),
            "ENCRYPTION_KEY": generate_key().decode("utf-8"),
            "PORT": port,
            "AUTH_DOMAIN": f"{host}:{port}",
            "AUTH_MAIN_USER_EMAIL": user_email,
            "AUTH_MAIN_USER_PASSWORD": user_password,
        }
        if not ssl:
            environment_variables.update(
                {
                    "CSRF_COOKIE_SECURE": False,
                    "SESSION_DATA_COOKIE_SECURE": False,
                    "USER_LOCALE_COOKIE_SECURE": False,
                    "LOGIN_HINT_COOKIE_SECURE": False,
                    "LOGIN_SESSION_COOKIE_SECURE": False,
                    "REGISTRATION_SESSION_COOKIE_SECURE": False,
                    "SESSION_COOKIE_SECURE": False,
                    "AUTH_ADMIN_SESSION_COOKIE_SECURE": False,
                }
            )

        if docker:
            parts = [
                "docker run",
                "--name auth-server",
                f"-p {port}:{port}",
                "-d",
                *[
                    f'-e "{name}={value}"'
                    for (name, value) in environment_variables.items()
                ],
                "ghcr.io/auth-dev/auth:latest",
            ]
            typer.echo(" \\\n  ".join(parts))
        else:
            for name, value in environment_variables.items():
                typer.echo(f"{typer.style(name, bold=True)}={value}")

    @app.callback()
    def callback():
        pass

    return app
