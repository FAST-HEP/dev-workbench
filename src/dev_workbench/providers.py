"""Remote repository discovery with explicit credentials."""

import json
import subprocess
import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit


def credential(provider, host, args):
    if args.token_file:
        token = Path(args.token_file).read_text(encoding="utf-8").strip()
    else:
        choice = args.auth
        if not choice:
            if not sys.stdin.isatty():
                raise ValueError("Select a credential with --token-file or --auth.")
            print(f"Credentials for {host}")
            print("1. Use the active CLI credential (may have broad access or come from the environment)")
            print("2. Enter a dedicated fine-grained token")
            print("3. Read a token file")
            choice = input("Choose 1, 2, or 3: ").strip()
        if choice in {"1", "cli"}:
            print(f"Using the active credential for {host}. It may have broad permissions.")
            return None if provider == "gitlab" else cli_token(host)
        elif choice in {"2", "prompt"}:
            if not sys.stdin.isatty():
                raise ValueError("Entering a token requires a terminal.")
            token = getpass(f"Token for {host}: ").strip()
        elif choice == "3":
            token = Path(input("Token file: ").strip()).expanduser().read_text(encoding="utf-8").strip()
        else:
            raise ValueError("Select a credential with --token-file or --auth.")
    if not token:
        raise ValueError("The selected credential is empty.")
    return token


def cli_token(host):
    result = subprocess.run(
        ["gh", "auth", "token", "--hostname", host], capture_output=True, text=True
    )
    if result.returncode:
        raise ValueError(f"Could not read the active gh credential for {host}.")
    return result.stdout.strip()


def gitlab_cli_projects(host, namespace, include_subgroups, url_field):
    parameters = urlencode({"with_shared": "false",
                            "include_subgroups": str(include_subgroups).lower()})
    endpoint = f"groups/{quote(namespace, safe='')}/projects?{parameters}"
    result = subprocess.run(
        ["glab", "api", "--hostname", host, "--paginate", "--output", "json", endpoint],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError("glab could not list the group's projects.")
    projects = json.loads(result.stdout)
    if not isinstance(projects, list):
        raise ValueError("Unexpected project list from glab.")
    return [(repo["path_with_namespace"].removeprefix(f"{namespace}/"),
             repo[url_field]) for repo in projects]


def discover(source, args):
    provider = source["provider"]
    namespace = source["namespace"]
    if provider not in {"github", "gitlab"}:
        raise ValueError(f"Unsupported discovery provider: {provider}")
    host = source.get("host", f"{provider}.com")
    parsed = urlsplit(f"https://{host}")
    if (not parsed.hostname or parsed.username or parsed.path or parsed.query or parsed.fragment
            or any(character.isspace() for character in host)):
        raise ValueError("Use a hostname with an optional port for discovery.")
    token = credential(provider, host, args)
    use_ssh = source.get("clone_protocol", "ssh") == "ssh"
    if provider == "github":
        from github import Auth, Github

        api = "https://api.github.com" if host == "github.com" else f"https://{host}/api/v3"
        with Github(base_url=api, auth=Auth.Token(token)) as client:
            return [(repo.name, repo.ssh_url if use_ssh else repo.clone_url)
                    for repo in client.get_organization(namespace).get_repos()]
    include_subgroups = source.get("include_subgroups", False)
    url_field = "ssh_url_to_repo" if use_ssh else "http_url_to_repo"
    if token is None:
        return gitlab_cli_projects(host, namespace, include_subgroups, url_field)

    from gitlab import Gitlab

    with Gitlab(f"https://{host}", private_token=token) as client:
        group = client.groups.get(namespace, lazy=True)
        projects = group.projects.list(iterator=True, with_shared=False,
                                       include_subgroups=include_subgroups)
        return [(repo.path_with_namespace.removeprefix(f"{namespace}/"),
                 getattr(repo, url_field)) for repo in projects]
