from __future__ import annotations

"""
supabase.py — Supabase client setup for PettyCrimeSG.

This module handles connecting to the Supabase database. It:
  1. Loads credentials from the .env file (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
  2. Provides a cached client so we only open one connection across the whole app
  3. Provides a helper to check if Supabase is configured (so other code can
     gracefully fall back to JSON files when the database is not yet set up)

Required environment variables (add these to your .env file):
    SUPABASE_URL              - The URL of your Supabase project
                                Example: https://abcdefgh.supabase.co
    SUPABASE_SERVICE_ROLE_KEY - The service role key (preferred for backend use,
                                has full database access bypassing Row Level Security)
    SUPABASE_ANON_KEY         - The anonymous/public key (fallback if service role not set,
                                restricted by Row Level Security policies)

See .env.example for a template.
"""

import os
from functools import lru_cache

# python-dotenv loads variables from a .env file into os.environ so we can
# access them with os.getenv(). We call load_dotenv() at import time so
# credentials are available as soon as this module is imported.
from dotenv import load_dotenv

# load_dotenv() looks for a .env file starting from the current directory and
# walking up the directory tree. It will find our root-level .env automatically.
load_dotenv()


def is_supabase_configured() -> bool:
    """
    Check whether the required Supabase environment variables have been set.

    This is useful for deciding whether to use the database or fall back to
    reading from JSON files (for development without a Supabase project).

    Returns:
        True  - Both SUPABASE_URL and a key (service role or anon) are present.
        False - One or both required values are missing or empty.

    Example:
        if is_supabase_configured():
            incidents = get_all_incidents()   # read from database
        else:
            incidents = load_from_json_file() # read from local file
    """
    # Read both possible credential values from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )

    # bool("") is False, bool("https://...") is True — so this handles empty strings too
    return bool(supabase_url) and bool(supabase_key)


@lru_cache(maxsize=1)
def get_supabase_client():
    """
    Create and return a cached Supabase client.

    The @lru_cache decorator means this function only runs ONCE. After the first
    call, Python returns the same client object every time. This is important
    because opening a new database connection on every request is slow and wasteful.

    Why use the service role key for backend?
    The service role key bypasses Supabase's Row Level Security (RLS) policies,
    which is what we want for server-side code. The anon key is for frontend/public
    use where RLS should restrict what users can access.

    Returns:
        A supabase.Client object ready to make queries.

    Raises:
        RuntimeError: If the environment variables are missing.
        RuntimeError: If the supabase Python package is not installed.

    Example:
        client = get_supabase_client()
        response = client.table("incidents").select("*").execute()
        print(response.data)
    """
    # Read credentials from environment (populated by load_dotenv() above)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )

    # Fail fast with a helpful error message if credentials are missing
    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Missing Supabase credentials.\n"
            "Please create a .env file in the project root and add:\n"
            "  SUPABASE_URL=https://your-project-id.supabase.co\n"
            "  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key\n"
            "See .env.example for a template."
        )

    # Import here so the rest of the app can still import this module
    # even if the supabase package is not installed (it will just fail when
    # get_supabase_client() is actually called, not at import time)
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "The Supabase Python SDK is not installed.\n"
            "Run this command to install it:\n"
            "  pip install supabase\n"
            "Or install all dependencies with:\n"
            "  pip install -r backend/requirements.txt"
        ) from exc

    # Create the client using the URL and key
    return create_client(supabase_url, supabase_key)
