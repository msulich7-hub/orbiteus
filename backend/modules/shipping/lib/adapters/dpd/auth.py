"""DPD credentials — port of mercato-shipping-hub dpd-auth.ts."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DpdCredentials:
    login: str
    password: str
    master_fid: int
    fid: int


def resolve_dpd_credentials() -> DpdCredentials:
    login = (os.environ.get("DPD_LOGIN") or "").strip()
    password = (os.environ.get("DPD_PASSWORD") or "").strip()
    master_raw = (os.environ.get("DPD_MASTER_FID") or "").strip()

    if not login or not password or not master_raw:
        raise RuntimeError(
            "Missing DPD credentials. Set DPD_LOGIN, DPD_PASSWORD, DPD_MASTER_FID environment variables."
        )

    try:
        master_fid = int(master_raw)
    except ValueError as exc:
        raise RuntimeError(f'DPD_MASTER_FID must be a number, got: "{master_raw}"') from exc

    fid_raw = (os.environ.get("DPD_FID") or "").strip()
    fid = int(fid_raw) if fid_raw else master_fid

    return DpdCredentials(login=login, password=password, master_fid=master_fid, fid=fid)
