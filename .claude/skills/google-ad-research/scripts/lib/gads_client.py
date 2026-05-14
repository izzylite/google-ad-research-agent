"""lib/gads_client.py — Google Ads API client builder.

Loads creds from environment (set by lib.config.load_env() upstream) and
returns a configured GoogleAdsClient. login_customer_id is per-call
overridable to handle MCC-vs-direct access patterns.

Required env vars:
    GOOGLE_ADS_DEVELOPER_TOKEN
    GOOGLE_ADS_CLIENT_ID
    GOOGLE_ADS_CLIENT_SECRET
    GOOGLE_ADS_REFRESH_TOKEN
    GOOGLE_ADS_LOGIN_CUSTOMER_ID (default; can be overridden per-call)
    GOOGLE_ADS_CUSTOMER_ID (target account; can be overridden per-call)
"""
from __future__ import annotations

import os

REQUIRED_GADS_ENV = (
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
)


def build_gads_client(*, login_customer_id: str | None = None):
    """Build google-ads-python client from .env.

    login_customer_id overrides the env default — useful when querying a
    customer directly (login = target) vs through an MCC parent.

    Returns:
        google.ads.googleads.client.GoogleAdsClient
    """
    # Import inside function so test fixtures can monkeypatch before import
    # when google-ads-python isn't installed yet.
    from google.ads.googleads.client import GoogleAdsClient

    missing = [k for k in REQUIRED_GADS_ENV if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Google Ads env vars missing: {missing}. "
            f"Copy from appflow_google_ads_api_team_starter/google-ads.yaml "
            f"into root .env."
        )

    login = login_customer_id or os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]

    config = {
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": login,
        "use_proto_plus": True,
    }
    return GoogleAdsClient.load_from_dict(config)


def get_target_customer_id() -> str:
    """Read GOOGLE_ADS_CUSTOMER_ID. Default target account for queries."""
    cid = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    if not cid:
        raise EnvironmentError(
            "GOOGLE_ADS_CUSTOMER_ID not set. Add to .env."
        )
    return cid
