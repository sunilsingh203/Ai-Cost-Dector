import json
import os
import shutil
import subprocess
from typing import Any


class AzureCLIError(Exception):
    """Base error for Azure CLI failures."""


class AzureCLINotInstalledError(AzureCLIError):
    pass


class AzureCLINotLoggedInError(AzureCLIError):
    pass


class ResourceGroupNotFoundError(AzureCLIError):
    pass


def _ensure_az_available() -> str:
    az_candidates = []
    if os.environ.get("AZURE_CLI_PATH"):
        az_candidates.append(os.environ["AZURE_CLI_PATH"])
    az_candidates.extend(["az", "az.cmd", "az.exe"])

    for candidate in az_candidates:
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    fallback_paths = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az",
    ]
    for path in fallback_paths:
        if os.path.exists(path):
            return path

    raise AzureCLINotInstalledError(
        "Azure CLI is not installed or not on PATH. Install it from https://aka.ms/installazurecli"
    )


def _run_az(args: list[str], *, context: str | None = None) -> Any:
    az_path = _ensure_az_available()
    try:
        result = subprocess.run(
            [az_path, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AzureCLINotInstalledError(
            "Azure CLI is not installed or not on PATH. Install it from https://aka.ms/installazurecli"
        ) from exc

    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()

    if result.returncode != 0:
        combined = f"{stderr}\n{stdout}".lower()
        if any(
            phrase in combined
            for phrase in (
                "please run 'az login'",
                "please run az login",
                "not logged in",
                "no subscriptions found",
                "authentication failed",
            )
        ):
            raise AzureCLINotLoggedInError(
                "Azure CLI is not logged in. Run 'az login' and try again."
            )
        if "resourcegroup" in combined and (
            "could not be found" in combined
            or "not found" in combined
            or "does not exist" in combined
        ):
            raise ResourceGroupNotFoundError(
                f"Resource group not found: {context or 'unknown'}"
            )
        raise AzureCLIError(stderr or stdout or "Azure CLI command failed.")

    if not stdout:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AzureCLIError("Failed to parse Azure CLI JSON output.") from exc


def list_resource_groups() -> list[dict[str, str]]:
    groups = _run_az(["group", "list", "-o", "json"])
    if not isinstance(groups, list):
        raise AzureCLIError("Unexpected response from 'az group list'.")

    return [
        {
            "name": group.get("name", ""),
            "location": group.get("location", ""),
        }
        for group in groups
        if group.get("name")
    ]


def _normalize_sku(resource: dict[str, Any]) -> str | None:
    sku = resource.get("sku")
    if not sku:
        return None
    if isinstance(sku, str):
        return sku
    if isinstance(sku, dict):
        parts = [sku.get("name"), sku.get("tier"), sku.get("size"), sku.get("family")]
        joined = " / ".join(part for part in parts if part)
        return joined or None
    return str(sku)


def list_resources(resource_group: str) -> list[dict[str, Any]]:
    resources = _run_az(
        ["resource", "list", "--resource-group", resource_group, "-o", "json"],
        context=resource_group,
    )
    if not isinstance(resources, list):
        raise AzureCLIError("Unexpected response from 'az resource list'.")

    return [
        {
            "type": resource.get("type"),
            "name": resource.get("name"),
            "location": resource.get("location"),
            "sku": _normalize_sku(resource),
            "tags": resource.get("tags") or {},
        }
        for resource in resources
    ]
