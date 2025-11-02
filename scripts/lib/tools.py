#!/usr/bin/env python3
"""
Tool validation utilities for data processing pipeline.
Ensures required external tools are available before running long operations.
"""

import shutil
import subprocess
import sys
from typing import List, Tuple, Optional, Dict
from pathlib import Path


def check_tool(tool: str) -> bool:
    """
    Check if an external tool is available in the system PATH.

    Args:
        tool: Name of the tool to check

    Returns:
        True if the tool is available, False otherwise
    """
    return shutil.which(tool) is not None


def get_tool_version(tool: str, version_flag: str = "--version") -> Optional[str]:
    """
    Get the version string for a tool.

    Args:
        tool: Name of the tool
        version_flag: Flag to use for version check (default: --version)

    Returns:
        Version string if available, None otherwise
    """
    if not check_tool(tool):
        return None

    try:
        result = subprocess.run(
            [tool, version_flag],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Some tools output to stderr instead of stdout
        output = result.stdout or result.stderr

        # Return first non-empty line (usually contains version)
        for line in output.strip().split('\n'):
            if line.strip():
                return line.strip()

        return "Unknown version"

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return None


def validate_tools(required: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that required external tools are available.

    Args:
        required: List of tool names that must be present

    Returns:
        Tuple of (all_present, missing_tools)
    """
    missing = [tool for tool in required if not check_tool(tool)]
    return len(missing) == 0, missing


def check_python_package(package: str) -> bool:
    """
    Check if a Python package is installed.

    Args:
        package: Name of the Python package

    Returns:
        True if installed, False otherwise
    """
    try:
        import importlib
        importlib.import_module(package)
        return True
    except ImportError:
        return False


def validate_python_packages(required: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that required Python packages are installed.

    Args:
        required: List of package names that must be installed

    Returns:
        Tuple of (all_present, missing_packages)
    """
    missing = [pkg for pkg in required if not check_python_package(pkg)]
    return len(missing) == 0, missing


# Common tool sets for different operations
RASTER_TOOLS = [
    'gdal_translate',
    'gdalwarp',
    'gdal2tiles.py',
    'gdaldem',
    'gdal_contour',
    'gdalinfo'
]

VECTOR_TOOLS = [
    'ogr2ogr',
    'ogrinfo',
    'tippecanoe'
]

PMTILES_TOOLS = [
    'pmtiles',
    'mb-util'
]

WHITEBOX_TOOLS = [
    # WhiteboxTools is typically a Python package, not a CLI tool
    # Check via Python import instead
]


def print_tool_status(tools: List[str], verbose: bool = False) -> None:
    """
    Print the status of required tools.

    Args:
        tools: List of tools to check
        verbose: If True, show version information
    """
    print("\n=== Tool Availability Check ===\n")

    max_tool_len = max(len(tool) for tool in tools)

    for tool in tools:
        available = check_tool(tool)
        status = "✓" if available else "✗"
        status_text = "Available" if available else "Missing"

        if verbose and available:
            version = get_tool_version(tool)
            if version:
                print(f"{status} {tool:<{max_tool_len}} : {status_text} ({version})")
            else:
                print(f"{status} {tool:<{max_tool_len}} : {status_text}")
        else:
            print(f"{status} {tool:<{max_tool_len}} : {status_text}")

    print()


def ensure_tools_available(
    required: List[str],
    exit_on_missing: bool = True,
    verbose: bool = False
) -> bool:
    """
    Ensure required tools are available, with helpful error messages.

    Args:
        required: List of required tool names
        exit_on_missing: If True, exit the program if tools are missing
        verbose: If True, show detailed information

    Returns:
        True if all tools are available, False otherwise
    """
    all_present, missing = validate_tools(required)

    if verbose or not all_present:
        print_tool_status(required, verbose=verbose)

    if not all_present:
        print(f"ERROR: Missing required tools: {', '.join(missing)}\n")

        # Provide installation hints
        print("Installation hints:")

        if any(tool.startswith('gdal') or tool.startswith('ogr') for tool in missing):
            print("  • GDAL tools: conda install -c conda-forge gdal")
            print("               or: brew install gdal (macOS)")
            print("               or: sudo apt-get install gdal-bin (Ubuntu)")

        if 'tippecanoe' in missing:
            print("  • Tippecanoe: brew install tippecanoe (macOS)")
            print("               or: see https://github.com/felt/tippecanoe")

        if 'pmtiles' in missing:
            print("  • PMTiles: pip install pmtiles")
            print("            or: npm install -g pmtiles")

        if 'mb-util' in missing:
            print("  • mb-util: pip install mb-util")

        print()

        if exit_on_missing:
            sys.exit(1)

        return False

    if verbose:
        print("All required tools are available!\n")

    return True


def ensure_python_packages_available(
    required: List[str],
    exit_on_missing: bool = True
) -> bool:
    """
    Ensure required Python packages are installed.

    Args:
        required: List of required package names
        exit_on_missing: If True, exit the program if packages are missing

    Returns:
        True if all packages are available, False otherwise
    """
    all_present, missing = validate_python_packages(required)

    if not all_present:
        print(f"ERROR: Missing required Python packages: {', '.join(missing)}\n")
        print(f"Install with: pip install {' '.join(missing)}\n")

        if exit_on_missing:
            sys.exit(1)

        return False

    return True


def get_gdal_version() -> Optional[Tuple[int, int, int]]:
    """
    Get the GDAL version as a tuple of (major, minor, patch).

    Returns:
        Version tuple if available, None otherwise
    """
    version_str = get_tool_version('gdalinfo')
    if not version_str:
        return None

    # Parse version from string like "GDAL 3.5.1, released 2022/06/30"
    import re
    match = re.search(r'GDAL (\d+)\.(\d+)\.(\d+)', version_str)
    if match:
        return tuple(int(x) for x in match.groups())

    return None


def check_gdal_minimum_version(
    min_major: int = 3,
    min_minor: int = 0,
    min_patch: int = 0
) -> bool:
    """
    Check if GDAL meets minimum version requirements.

    Args:
        min_major: Minimum major version
        min_minor: Minimum minor version
        min_patch: Minimum patch version

    Returns:
        True if version meets requirements, False otherwise
    """
    version = get_gdal_version()
    if not version:
        return False

    major, minor, patch = version

    if major > min_major:
        return True
    elif major == min_major:
        if minor > min_minor:
            return True
        elif minor == min_minor:
            return patch >= min_patch

    return False


# Convenience function for scripts to use
def validate_environment_for_tile_generation() -> bool:
    """
    Validate the environment has all tools needed for tile generation.

    Returns:
        True if environment is ready, False otherwise
    """
    print("Checking environment for tile generation...\n")

    # Check external tools
    all_tools = RASTER_TOOLS + VECTOR_TOOLS + PMTILES_TOOLS
    tools_ok = ensure_tools_available(all_tools, exit_on_missing=False, verbose=True)

    # Check Python packages
    python_packages = ['rasterio', 'geopandas', 'click', 'shapely']
    packages_ok = ensure_python_packages_available(python_packages, exit_on_missing=False)

    # Check GDAL version
    if tools_ok:
        if check_gdal_minimum_version(3, 0, 0):
            print("✓ GDAL version meets requirements (≥3.0.0)\n")
        else:
            print("✗ GDAL version is too old (need ≥3.0.0)\n")
            tools_ok = False

    return tools_ok and packages_ok


if __name__ == "__main__":
    """
    Command-line tool checker utility.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Check for required tools")
    parser.add_argument(
        '--check',
        choices=['all', 'raster', 'vector', 'pmtiles', 'tiles'],
        default='all',
        help='Which tool set to check'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show version information'
    )

    args = parser.parse_args()

    if args.check == 'raster':
        tools = RASTER_TOOLS
    elif args.check == 'vector':
        tools = VECTOR_TOOLS
    elif args.check == 'pmtiles':
        tools = PMTILES_TOOLS
    elif args.check == 'tiles' or args.check == 'all':
        tools = RASTER_TOOLS + VECTOR_TOOLS + PMTILES_TOOLS
    else:
        tools = []

    if tools:
        success = ensure_tools_available(tools, exit_on_missing=False, verbose=args.verbose)
        sys.exit(0 if success else 1)