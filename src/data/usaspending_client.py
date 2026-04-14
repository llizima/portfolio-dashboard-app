"""
Reusable USAspending API client for the Applied Government Analytics (AGA) Value Dashboard project.

This module provides a production-minded request layer for USAspending
endpoints, beginning with the spending_by_award search endpoint used by the
current benchmarking workflow.

Key capabilities:
- reusable POST request wrapper
- retry/backoff for transient failures
- pagination handling
- optional raw JSON persistence for auditability
- structured logging
"""

from __future__ import annotations

import copy
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests import Response, Session
from requests.exceptions import ConnectionError, Timeout

from src.config import RAW_DATA_DIR, ensure_directories


class USAspendingClientError(Exception):
    """Base exception for USAspending client failures."""


class USAspendingRequestError(USAspendingClientError):
    """Raised when a USAspending request fails permanently."""


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    backoff_factor: float = 1.5
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass(frozen=True)
class RequestConfig:
    """Configuration for request behavior."""

    timeout: int = 60
    page_size: int = 100


class USAspendingClient:
    """
    Reusable client for USAspending API access.

    Parameters
    ----------
    base_url : str
        Base USAspending API URL.
    session : requests.Session | None
        Optional injected session for testing or advanced usage.
    timeout : int
        Default request timeout in seconds.
    max_retries : int
        Maximum number of retries for retryable failures.
    backoff_factor : float
        Exponential backoff factor for retry wait times.
    logger : logging.Logger | None
        Optional logger. If not provided, a module logger is used.
    """

    SEARCH_SPENDING_BY_AWARD_ENDPOINT = "api/v2/search/spending_by_award/"

    def __init__(
        self,
        base_url: str = "https://api.usaspending.gov/",
        session: Session | None = None,
        timeout: int = 60,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = session or requests.Session()
        self.request_config = RequestConfig(timeout=timeout)
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )
        self.logger = logger or logging.getLogger(__name__)

    def search_spending_by_award(
        self,
        payload: dict[str, Any],
        *,
        save_raw: bool = False,
        raw_save_dir: Path | None = None,
        raw_file_stem: str | None = None,
        save_mode: str = "combined",
    ) -> dict[str, Any]:
        """
        Fetch all paginated results from the spending_by_award endpoint.

        Parameters
        ----------
        payload : dict[str, Any]
            Base POST payload for the endpoint.
        save_raw : bool, default False
            Whether to save raw JSON output to disk.
        raw_save_dir : Path | None, default None
            Optional directory for raw JSON output. Defaults to
            RAW_DATA_DIR/usaspending.
        raw_file_stem : str | None, default None
            Optional file stem used when saving raw JSON.
        save_mode : str, default "combined"
            Raw save behavior. Supported values:
            - "combined": save one combined JSON file containing all results
            - "pages": save one JSON file per page response

        Returns
        -------
        dict[str, Any]
            Dictionary with aggregated results and run metadata.
        """
        endpoint = self.SEARCH_SPENDING_BY_AWARD_ENDPOINT
        return self._fetch_all_pages(
            endpoint=endpoint,
            payload=payload,
            save_raw=save_raw,
            raw_save_dir=raw_save_dir,
            raw_file_stem=raw_file_stem,
            save_mode=save_mode,
        )

    def _fetch_all_pages(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        save_raw: bool,
        raw_save_dir: Path | None,
        raw_file_stem: str | None,
        save_mode: str,
    ) -> dict[str, Any]:
        """
        Iterate through paginated API responses and aggregate results.
        """
        if save_mode not in {"combined", "pages"}:
            raise ValueError("save_mode must be either 'combined' or 'pages'.")

        request_payload = copy.deepcopy(payload)
        request_payload.setdefault("page", 1)

        all_results: list[dict[str, Any]] = []
        pages_fetched = 0
        saved_files: list[Path] = []
        page_metadata_history: list[dict[str, Any]] = []

        page = int(request_payload["page"])

        while True:
            request_payload["page"] = page

            self.logger.info(
                "Requesting USAspending page",
                extra={
                    "endpoint": endpoint,
                    "page": page,
                    "limit": request_payload.get("limit"),
                    "filters": request_payload.get("filters"),
                },
            )

            data = self._post(endpoint=endpoint, payload=request_payload)
            pages_fetched += 1

            meta = data.get("page_metadata", {}) or {}
            page_metadata_history.append(meta)

            if save_raw and save_mode == "pages":
                save_path = self._save_raw_json(
                    content=data,
                    raw_save_dir=raw_save_dir,
                    raw_file_stem=raw_file_stem,
                    suffix=f"_page_{page}",
                )
                saved_files.append(save_path)
                self.logger.info(
                    "Saved raw USAspending page response",
                    extra={"path": str(save_path), "page": page},
                )

            results = data.get("results", []) or []
            all_results.extend(results)

            has_next = bool(meta.get("hasNext", False))

            self.logger.info(
                "Processed USAspending page",
                extra={
                    "page": page,
                    "page_result_count": len(results),
                    "total_results_so_far": len(all_results),
                    "has_next": has_next,
                },
            )

            if not results or not has_next:
                break

            page += 1

        combined_output = {
            "results": all_results,
            "page_metadata": {
                "pages_fetched": pages_fetched,
                "last_page": page,
                "has_next_final": False,
            },
            "request_metadata": {
                "endpoint": endpoint,
                "base_payload": payload,
                "raw_saved": save_raw,
                "save_mode": save_mode if save_raw else None,
                "saved_files": [str(path) for path in saved_files],
            },
            "page_metadata_history": page_metadata_history,
        }

        if save_raw and save_mode == "combined":
            save_path = self._save_raw_json(
                content=combined_output,
                raw_save_dir=raw_save_dir,
                raw_file_stem=raw_file_stem,
                suffix="_combined",
            )
            saved_files.append(save_path)
            combined_output["request_metadata"]["saved_files"] = [
                str(path) for path in saved_files
            ]
            self.logger.info(
                "Saved combined raw USAspending output",
                extra={"path": str(save_path), "pages_fetched": pages_fetched},
            )

        self.logger.info(
            "Completed USAspending pagination run",
            extra={
                "endpoint": endpoint,
                "pages_fetched": pages_fetched,
                "total_results": len(all_results),
            },
        )

        return combined_output

    def _post(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a POST request with retry handling.

        Raises
        ------
        USAspendingRequestError
            If the request cannot be completed successfully.
        """
        url = self._build_url(endpoint)

        for attempt in range(1, self.retry_config.max_retries + 2):
            try:
                self.logger.info(
                    "Sending USAspending request",
                    extra={
                        "endpoint": endpoint,
                        "url": url,
                        "attempt": attempt,
                        "page": payload.get("page"),
                        "limit": payload.get("limit"),
                    },
                )

                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.request_config.timeout,
                )

                self._raise_for_retryable_http_errors(
                    response,
                    endpoint,
                    payload,
                    attempt,
                )
                return self._parse_json(response, endpoint)

            except (Timeout, ConnectionError) as exc:
                if not self._should_retry(attempt):
                    raise USAspendingRequestError(
                        "Request failed after retries for endpoint "
                        f"'{endpoint}'."
                    ) from exc

                self._sleep_before_retry(
                    attempt,
                    reason=str(exc),
                    endpoint=endpoint,
                )

            except USAspendingRequestError:
                if not self._should_retry(attempt):
                    raise

                self._sleep_before_retry(
                    attempt,
                    reason="retryable HTTP status",
                    endpoint=endpoint,
                )

        raise USAspendingRequestError(
            f"Request failed after retries for endpoint '{endpoint}'."
        )

    def _raise_for_retryable_http_errors(
        self,
        response: Response,
        endpoint: str,
        payload: dict[str, Any],
        attempt: int,
    ) -> None:
        """
        Raise a client error for retryable or terminal HTTP failures.
        """
        status_code = response.status_code

        if 200 <= status_code < 300:
            return

        message = (
            f"USAspending request failed: endpoint='{endpoint}', "
            f"status_code={status_code}, attempt={attempt}, "
            f"page={payload.get('page')}"
        )

        if status_code in self.retry_config.retry_status_codes:
            raise USAspendingRequestError(message)

        raise USAspendingRequestError(
            f"{message}. Non-retryable status returned by server."
        )

    def _parse_json(self, response: Response, endpoint: str) -> dict[str, Any]:
        """
        Parse JSON response safely.
        """
        try:
            data = response.json()
        except ValueError as exc:
            raise USAspendingRequestError(
                f"Invalid JSON returned by endpoint '{endpoint}'."
            ) from exc

        if not isinstance(data, dict):
            raise USAspendingRequestError(
                f"Unexpected response shape from endpoint '{endpoint}': "
                f"expected dict, got {type(data).__name__}."
            )

        return data

    def _build_url(self, endpoint: str) -> str:
        """Build full endpoint URL."""
        return self.base_url + endpoint.lstrip("/")

    def _should_retry(self, attempt: int) -> bool:
        """Return whether another retry should be attempted."""
        return attempt <= self.retry_config.max_retries

    def _sleep_before_retry(
        self,
        attempt: int,
        *,
        reason: str,
        endpoint: str,
    ) -> None:
        """
        Sleep using exponential backoff before retrying.
        """
        wait_seconds = self.retry_config.backoff_factor**attempt
        self.logger.warning(
            "Retrying USAspending request after transient failure",
            extra={
                "endpoint": endpoint,
                "attempt": attempt,
                "wait_seconds": wait_seconds,
                "reason": reason,
            },
        )
        time.sleep(wait_seconds)

    def _save_raw_json(
        self,
        *,
        content: dict[str, Any],
        raw_save_dir: Path | None,
        raw_file_stem: str | None,
        suffix: str = "",
    ) -> Path:
        """
        Save raw JSON content to disk in a readable format.
        """
        ensure_directories()

        base_dir = raw_save_dir or (RAW_DATA_DIR / "usaspending")
        base_dir.mkdir(parents=True, exist_ok=True)

        stem = raw_file_stem or self._default_raw_file_stem()
        file_path = base_dir / f"{stem}{suffix}.json"

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        return file_path

    @staticmethod
    def _default_raw_file_stem() -> str:
        """Generate a UTC timestamp-based file stem."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"usaspending_raw_{timestamp}"
