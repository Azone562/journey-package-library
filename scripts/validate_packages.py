import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PACKAGE_DIRECTORY = REPOSITORY_ROOT / "source" / "packages"

SUPPORTED_SCHEMA_VERSION = 3

SUPPORTED_JOURNEY_TYPES = {
    "STATE_PARKS",
    "NATIONAL_PARKS",
    "STADIUMS",
}

SUPPORTED_ICONS = {
    "tree",
    "park",
    "stadium",
}


class ValidationError:
    """Represents one validation problem found in a Journey package."""

    def __init__(self, file_name: str, message: str):
        self.file_name = file_name
        self.message = message

    def __str__(self) -> str:
        return f"{self.file_name}: {self.message}"


def load_package(package_path: Path) -> tuple[dict | None, list[ValidationError]]:
    """Loads one Journey package and reports malformed JSON cleanly."""

    try:
        with package_path.open(
            mode="r",
            encoding="utf-8",
        ) as package_file:
            return json.load(package_file), []

    except json.JSONDecodeError as exception:
        return None, [
            ValidationError(
                package_path.name,
                (
                    "Invalid JSON at "
                    f"line {exception.lineno}, "
                    f"column {exception.colno}: "
                    f"{exception.msg}"
                ),
            )
        ]


def require_non_blank_string(
    value,
    field_name: str,
    package_path: Path,
    errors: list[ValidationError],
) -> None:
    """Requires a value to be a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        errors.append(
            ValidationError(
                package_path.name,
                f"'{field_name}' must be a non-blank string.",
            )
        )


def validate_coordinates(
    item: dict,
    item_label: str,
    package_path: Path,
    errors: list[ValidationError],
) -> None:
    """Validates latitude and longitude for one Journey place."""

    latitude = item.get("latitude")
    longitude = item.get("longitude")

    if not isinstance(latitude, (int, float)):
        errors.append(
            ValidationError(
                package_path.name,
                f"{item_label}: latitude must be numeric.",
            )
        )
    elif not -90 <= latitude <= 90:
        errors.append(
            ValidationError(
                package_path.name,
                f"{item_label}: latitude must be between -90 and 90.",
            )
        )

    if not isinstance(longitude, (int, float)):
        errors.append(
            ValidationError(
                package_path.name,
                f"{item_label}: longitude must be numeric.",
            )
        )
    elif not -180 <= longitude <= 180:
        errors.append(
            ValidationError(
                package_path.name,
                f"{item_label}: longitude must be between -180 and 180.",
            )
        )


def validate_package(
    package_path: Path,
    package_data: dict,
) -> list[ValidationError]:
    """Validates one complete Journey package."""

    errors: list[ValidationError] = []

    schema_version = package_data.get("schemaVersion")

    if schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            ValidationError(
                package_path.name,
                (
                    f"Unsupported schemaVersion '{schema_version}'. "
                    f"Expected {SUPPORTED_SCHEMA_VERSION}."
                ),
            )
        )

    metadata = package_data.get("metadata")

    if not isinstance(metadata, dict):
        errors.append(
            ValidationError(
                package_path.name,
                "'metadata' must be an object.",
            )
        )
        return errors

    journey = package_data.get("journey")

    if not isinstance(journey, dict):
        errors.append(
            ValidationError(
                package_path.name,
                "'journey' must be an object.",
            )
        )
        return errors

    package_id = metadata.get("packageId")

    require_non_blank_string(
        package_id,
        "metadata.packageId",
        package_path,
        errors,
    )

    require_non_blank_string(
        metadata.get("displayName"),
        "metadata.displayName",
        package_path,
        errors,
    )

    package_version = metadata.get("packageVersion")

    if not isinstance(package_version, int) or package_version <= 0:
        errors.append(
            ValidationError(
                package_path.name,
                "'metadata.packageVersion' must be a positive integer.",
            )
        )

    journey_stable_key = journey.get("stableKey")

    require_non_blank_string(
        journey_stable_key,
        "journey.stableKey",
        package_path,
        errors,
    )

    if (
        isinstance(package_id, str)
        and isinstance(journey_stable_key, str)
        and package_id != journey_stable_key
    ):
        errors.append(
            ValidationError(
                package_path.name,
                (
                    "'metadata.packageId' and "
                    "'journey.stableKey' must match."
                ),
            )
        )

    journey_version = journey.get("version")

    if not isinstance(journey_version, int) or journey_version <= 0:
        errors.append(
            ValidationError(
                package_path.name,
                "'journey.version' must be a positive integer.",
            )
        )


    journey_type = journey.get("type")

    if journey_type not in SUPPORTED_JOURNEY_TYPES:
        errors.append(
            ValidationError(
                package_path.name,
                (
                    f"Unsupported Journey type '{journey_type}'. "
                    "Supported values: "
                    f"{', '.join(sorted(SUPPORTED_JOURNEY_TYPES))}."
                ),
            )
        )

    metadata_icon = metadata.get("icon")

    if metadata_icon not in SUPPORTED_ICONS:
        errors.append(
            ValidationError(
                package_path.name,
                (
                    f"Unsupported metadata icon '{metadata_icon}'. "
                    "Supported values: "
                    f"{', '.join(sorted(SUPPORTED_ICONS))}."
                ),
            )
        )

    journey_icon = journey.get("iconName")

    if journey_icon not in SUPPORTED_ICONS:
        errors.append(
            ValidationError(
                package_path.name,
                (
                    f"Unsupported Journey icon '{journey_icon}'. "
                    "Supported values: "
                    f"{', '.join(sorted(SUPPORTED_ICONS))}."
                ),
            )
        )


    items = journey.get("items")

    if not isinstance(items, list) or not items:
        errors.append(
            ValidationError(
                package_path.name,
                "'journey.items' must contain at least one place.",
            )
        )
        return errors

    stable_keys: set[str] = set()

    for index, item in enumerate(items):
        item_number = index + 1
        item_label = f"Item {item_number}"

        if not isinstance(item, dict):
            errors.append(
                ValidationError(
                    package_path.name,
                    f"{item_label} must be an object.",
                )
            )
            continue

        stable_key = item.get("stableKey")
        name = item.get("name")

        require_non_blank_string(
            stable_key,
            f"{item_label}.stableKey",
            package_path,
            errors,
        )

        require_non_blank_string(
            name,
            f"{item_label}.name",
            package_path,
            errors,
        )

        if isinstance(stable_key, str) and stable_key.strip():
            if stable_key in stable_keys:
                errors.append(
                    ValidationError(
                        package_path.name,
                        (
                            f"{item_label}: duplicate stableKey "
                            f"'{stable_key}'."
                        ),
                    )
                )
            else:
                stable_keys.add(stable_key)

        validate_coordinates(
            item,
            item_label,
            package_path,
            errors,
        )

    return errors


def main() -> int:
    """Validates every source Journey package."""

    if not SOURCE_PACKAGE_DIRECTORY.exists():
        print(
            "ERROR: Source package directory does not exist:"
        )
        print(SOURCE_PACKAGE_DIRECTORY)
        return 1

    package_paths = sorted(
        SOURCE_PACKAGE_DIRECTORY.glob("*.json")
    )

    if not package_paths:
        print("ERROR: No Journey packages were found.")
        return 1

    print(
        f"Validating {len(package_paths)} Journey package(s)..."
    )
    print()

    all_errors: list[ValidationError] = []
    package_ids: dict[str, str] = {}

    for package_path in package_paths:
        package_data, load_errors = load_package(
            package_path
        )

        if load_errors:
            all_errors.extend(load_errors)
            continue

        if package_data is None:
            continue

        package_errors = validate_package(
            package_path,
            package_data,
        )

        all_errors.extend(package_errors)

        metadata = package_data.get("metadata", {})

        if isinstance(metadata, dict):
            package_id = metadata.get("packageId")

            if isinstance(package_id, str) and package_id.strip():
                existing_file = package_ids.get(package_id)

                if existing_file is not None:
                    all_errors.append(
                        ValidationError(
                            package_path.name,
                            (
                                f"Duplicate packageId '{package_id}'. "
                                f"Already used by {existing_file}."
                            ),
                        )
                    )
                else:
                    package_ids[package_id] = package_path.name

    if all_errors:
        print(
            f"FAILED: {len(all_errors)} validation error(s) found."
        )
        print()

        for error in all_errors:
            print(f"  - {error}")

        return 1

    print(
        f"SUCCESS: {len(package_paths)} Journey package(s) are valid."
    )

    for package_path in package_paths:
        print(f"  - {package_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())