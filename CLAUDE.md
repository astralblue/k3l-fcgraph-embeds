# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library for normalizing Farcaster cast embeds into canonical forms. The package is structured as a namespace package under `k3l.fcgraph.embeds`.

### Farcaster Embeds Context

Farcaster is a decentralized social network where posts are called "casts". Each cast can contain an `embeds` field - an array of embed elements that can be:

1. **URL embeds**: Web URLs or Ethereum asset URIs (following CAIP-19 format)
   - Web URLs: `https://example.com`
   - NFT assets: `chain://eip155:1/erc721:0xa723.../11`
   - Collections: `chain://eip155:1/erc721:0xa723...`

2. **Quote casts**: References to other casts (like sharing/retweeting with commentary)
   - Uses CastId references for efficient storage
   - Implemented via FIP-2 specification

### Key Data Types

**CastId** (composite type):
- `fid` (uint64): Farcaster ID of the user who created the cast
- `hash` (bytes): Unique hash of the specific cast

**Embed** structure:
```
Embed {
  url: string (optional)
  cast_id: CastId (optional)
}
```

This library normalizes these various embed formats into canonical forms for consistent processing.

## Development Commands

### Environment Setup
Following project convention, use Python 3.9 (minimum supported version) for development:
```bash
# Create venv (using project convention)
python3.9 -m venv --prompt="k3l-fcgraph-embeds/py3.9" .venvs/py3.9

# Install development dependencies
.venvs/py3.9/bin/pip install -e ".[dev]"
```

### Code Quality
```bash
# Format code
.venvs/py3.9/bin/black .
.venvs/py3.9/bin/isort .

# Check formatting (useful for CI)
.venvs/py3.9/bin/black --check .
.venvs/py3.9/bin/isort --check-only .
```

### Testing
```bash
# Run tests
.venvs/py3.9/bin/pytest

# Run tests with coverage
.venvs/py3.9/bin/pytest --cov=k3l.fcgraph.embeds
```

### Building
```bash
# Build package
.venvs/py3.9/bin/python -m build
```

## Architecture

- **Package Structure**: Uses namespace packaging with `k3l.fcgraph.embeds` as the main module
- **Build System**: Uses `flit_core` as the build backend with dynamic versioning
- **Code Style**: Black formatter with isort (using Black profile) for import sorting
- **Python Support**: Python 3.9+ with explicit support through 3.13

## Configuration

- **Tool Configuration**: All tool configurations are in `pyproject.toml`
- **Import Sorting**: isort configured with Black profile for consistency
- **Version Management**: Dynamic versioning handled by flit from the `__version__` in `__init__.py`