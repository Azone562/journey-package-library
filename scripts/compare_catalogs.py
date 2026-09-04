import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

PRODUCTION_CATALOG_PATH = (
    REPOSITORY_ROOT
    / "catalog.json"
)

GENERATED_CATALOG_PATH = (
    REPOSITORY_ROOT
    / "generated_catalog.json"
)


FIELDS_TO_COMPARE = [
    "packageId",
    "packageVersion",
    "displayName",
    "description",
    "author",
    "icon",
    "accentColor",
    "category",
    "countryCode",
    "countryName",
    "journeyName",
    "journeyDescription",
    "regionCode",
    "placeCount",
    "packagePath",
]


def load_json(path: Path) -> dict:
    with path.open(
        mode="r",
        encoding="utf-8",
    ) as input_file:
        return json.load(
            input_file
        )


def packages_by_id(
    catalog: dict
) -> dict[str, dict]:
    return {
        package["packageId"]: package
        for package in catalog.get(
            "packages",
            [],
        )
    }


def main() -> int:
    if not PRODUCTION_CATALOG_PATH.exists():
        print(
            "ERROR: catalog.json was not found."
        )
        return 1

    if not GENERATED_CATALOG_PATH.exists():
        print(
            "ERROR: generated_catalog.json was not found."
        )
        return 1

    production_catalog = load_json(
        PRODUCTION_CATALOG_PATH
    )

    generated_catalog = load_json(
        GENERATED_CATALOG_PATH
    )

    production_packages = packages_by_id(
        production_catalog
    )

    generated_packages = packages_by_id(
        generated_catalog
    )

    production_ids = set(
        production_packages
    )

    generated_ids = set(
        generated_packages
    )

    problems: list[str] = []

    missing_from_generated = (
        production_ids
        - generated_ids
    )

    extra_in_generated = (
        generated_ids
        - production_ids
    )

    for package_id in sorted(
        missing_from_generated
    ):
        problems.append(
            (
                f"{package_id}: exists in production "
                "but not generated catalog."
            )
        )

    for package_id in sorted(
        extra_in_generated
    ):
        problems.append(
            (
                f"{package_id}: exists in generated "
                "catalog but not production."
            )
        )

    shared_ids = (
        production_ids
        & generated_ids
    )

    for package_id in sorted(
        shared_ids
    ):
        production_package = (
            production_packages[
                package_id
            ]
        )

        generated_package = (
            generated_packages[
                package_id
            ]
        )

        for field_name in (
            FIELDS_TO_COMPARE
        ):
            production_value = (
                production_package.get(
                    field_name
                )
            )

            generated_value = (
                generated_package.get(
                    field_name
                )
            )

            if (
                production_value
                != generated_value
            ):
                problems.append(
                    (
                        f"{package_id}: "
                        f"field '{field_name}' differs.\n"
                        f"    production: "
                        f"{production_value!r}\n"
                        f"    generated:  "
                        f"{generated_value!r}"
                    )
                )

    if problems:
        print(
            f"DIFFERENCES FOUND: "
            f"{len(problems)}"
        )
        print()

        for problem in problems:
            print(
                f"- {problem}"
            )
            print()

        return 1

    print(
        "SUCCESS: Generated catalog "
        "matches production metadata."
    )

    print(
        "Note: SHA-256 values are "
        "intentionally excluded from "
        "this comparison."
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )