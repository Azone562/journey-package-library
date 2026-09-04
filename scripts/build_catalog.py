import hashlib
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

SOURCE_PACKAGE_DIRECTORY = (
    REPOSITORY_ROOT
    / "source"
    / "packages"
)

GENERATED_PACKAGE_DIRECTORY = (
    REPOSITORY_ROOT
    / "packages"
)

GENERATED_CATALOG_PATH = (
    REPOSITORY_ROOT
    / "catalog.json"
)

CATALOG_SCHEMA_VERSION = 1


def calculate_sha256(file_path: Path) -> str:
    """
    Calculates the SHA-256 checksum from the exact bytes of a file.
    """

    digest = hashlib.sha256()

    with file_path.open("rb") as input_file:
        for chunk in iter(
            lambda: input_file.read(8192),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_package(package_path: Path) -> dict:
    """
    Loads one validated Journey package.
    """

    with package_path.open(
        mode="r",
        encoding="utf-8",
    ) as package_file:
        return json.load(package_file)


def optional_string(
    data: dict,
    key: str,
) -> str | None:
    """
    Returns a trimmed optional string from a JSON object.
    """

    value = data.get(key)

    if not isinstance(value, str):
        return None

    value = value.strip()

    return value or None


def build_catalog_entry(
    package_data: dict,
    published_package_path: Path,
) -> dict:
    """
    Builds the lightweight catalog entry consumed by the Android app.
    """

    metadata = package_data["metadata"]
    journey = package_data["journey"]
    items = journey["items"]

    entry = {
        "packageId": metadata["packageId"],
        "packageVersion": metadata["packageVersion"],
        "displayName": metadata["displayName"],
        "description": optional_string(
            metadata,
            "description",
        ),
        "author": optional_string(
            metadata,
            "author",
        ),
        "icon": optional_string(
            metadata,
            "icon",
        ),
        "accentColor": optional_string(
            metadata,
            "accentColor",
        ),
        "category": optional_string(
            metadata,
            "category",
        ),
        "countryCode": optional_string(
            metadata,
            "countryCode",
        ),
        "countryName": optional_string(
            metadata,
            "countryName",
        ),
        "journeyName": journey["name"],
        "journeyDescription": optional_string(
            journey,
            "description",
        ),
        "regionCode": optional_string(
            journey,
            "regionCode",
        ),
        "placeCount": len(items),
        "packagePath": (
            "packages/"
            + published_package_path.name
        ),
        "sha256": calculate_sha256(
            published_package_path
        ),
    }

    return entry


def determine_catalog_version() -> int:
    """
    Determines the temporary catalog version.

    During Milestone 1B we deliberately reuse the current production
    catalogVersion when possible. Automatic version management will be
    introduced only after the generated catalog has been verified.
    """

    production_catalog_path = (
        REPOSITORY_ROOT
        / "catalog.json"
    )

    if not production_catalog_path.exists():
        return 1

    try:
        with production_catalog_path.open(
            mode="r",
            encoding="utf-8",
        ) as catalog_file:
            production_catalog = json.load(
                catalog_file
            )

        catalog_version = production_catalog.get(
            "catalogVersion"
        )

        if (
            isinstance(catalog_version, int)
            and catalog_version > 0
        ):
            return catalog_version

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return 1


def prepare_generated_packages(
    source_package_paths: list[Path],
) -> list[Path]:
    """
    Creates deterministic published Journey package files.

    Source packages are parsed and rewritten using consistent JSON formatting
    and LF line endings. This ensures the same Journey package produces the
    same SHA-256 checksum regardless of whether the publishing workflow runs
    on Windows, macOS, or Linux.
    """

    if GENERATED_PACKAGE_DIRECTORY.exists():
        for existing_file in (
            GENERATED_PACKAGE_DIRECTORY.glob("*")
        ):
            if existing_file.is_file():
                existing_file.unlink()
    else:
        GENERATED_PACKAGE_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

    generated_paths: list[Path] = []

    for source_path in source_package_paths:
        package_data = load_package(
            source_path
        )

        generated_path = (
            GENERATED_PACKAGE_DIRECTORY
            / source_path.name
        )

        with generated_path.open(
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as generated_file:
            json.dump(
                package_data,
                generated_file,
                indent=2,
                ensure_ascii=False,
            )

            generated_file.write("\n")

        generated_paths.append(
            generated_path
        )

    return generated_paths


def main() -> int:
    """
    Generates the production Journey catalog and published package files
    from validated source packages.
    """

    if not SOURCE_PACKAGE_DIRECTORY.exists():
        print(
            "ERROR: Source package directory "
            "does not exist:"
        )
        print(SOURCE_PACKAGE_DIRECTORY)
        return 1

    source_package_paths = sorted(
        SOURCE_PACKAGE_DIRECTORY.glob(
            "*.json"
        )
    )

    if not source_package_paths:
        print(
            "ERROR: No Journey packages were found."
        )
        return 1

    print(
        f"Building catalog from "
        f"{len(source_package_paths)} "
        "Journey package(s)..."
    )
    print()

    generated_package_paths = (
        prepare_generated_packages(
            source_package_paths
        )
    )

    catalog_entries: list[dict] = []

    for (
        source_path,
        generated_path,
    ) in zip(
        source_package_paths,
        generated_package_paths,
    ):
        package_data = load_package(
            source_path
        )

        catalog_entry = build_catalog_entry(
            package_data=package_data,
            published_package_path=generated_path,
        )

        catalog_entries.append(
            catalog_entry
        )

        print(
            "  + "
            f"{catalog_entry['packageId']} "
            f"(v{catalog_entry['packageVersion']}, "
            f"{catalog_entry['placeCount']} places)"
        )

    catalog_entries.sort(
        key=lambda entry: (
            entry["displayName"].lower()
        )
    )

    catalog = {
        "catalogSchemaVersion":
            CATALOG_SCHEMA_VERSION,
        "catalogVersion":
            determine_catalog_version(),
        "packages":
            catalog_entries,
    }

    with GENERATED_CATALOG_PATH.open(
        mode="w",
        encoding="utf-8",
        newline="\n",
    ) as catalog_file:
        json.dump(
            catalog,
            catalog_file,
            indent=2,
            ensure_ascii=False,
        )

        catalog_file.write("\n")

    print()
    print(
        "SUCCESS: Production Journey catalog generated."
    )
    print(
        f"Catalog: {GENERATED_CATALOG_PATH}"
    )
    print(
        "Packages: "
        f"{GENERATED_PACKAGE_DIRECTORY}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())