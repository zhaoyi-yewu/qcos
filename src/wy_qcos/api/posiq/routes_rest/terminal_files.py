#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""REST endpoints for the QCOS web terminal file panel.

The four routes map to ``plans/terminal.md`` §4.4:

* ``GET    /v1/terminal/files``          — list directory
* ``POST   /v1/terminal/files/upload``   — upload a file (multipart)
* ``GET    /v1/terminal/files/download`` — download a file
* ``DELETE /v1/terminal/files``          — delete a file or empty dir

All endpoints require a QCOS JWT in the ``Authorization: Bearer ...``
header. Operations are scoped to the caller's own sandbox directory.
"""

from __future__ import annotations

import logging
import urllib.parse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    get_current_user_from_token,
    get_user_manager,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.common.config import Config
from wy_qcos.terminal import (
    FileNotFoundErrorInSandbox,
    FileService,
    FileServiceError,
    NotEmptyDirectoryError,
    PathEscapeError,
    TerminalAuditor,
    TerminalConfig,
    UploadTooLargeError,
)
from wy_qcos.user.user_manager import UserManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/terminal/files", tags=["terminal"])

# ``auto_error=False`` lets us return a 401 with our own detail message
# when the header is missing, instead of FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)


# ----------------------------------------------------------------------
# Dependencies
# ----------------------------------------------------------------------


def get_terminal_config() -> TerminalConfig:
    """Build the runtime config for terminal routes."""
    return TerminalConfig.from_config(Config.TERMINAL)


def get_current_terminal_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    user_manager: UserManager = Depends(get_user_manager),
) -> user_schemas.User:
    """Resolve the caller from the ``Authorization: Bearer`` header."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    user = get_current_user_from_token(credentials.credentials, user_manager)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        )
    return user


def get_file_service(
    user: user_schemas.User = Depends(get_current_terminal_user),
    cfg: TerminalConfig = Depends(get_terminal_config),
) -> FileService:
    """Build a :class:`FileService` scoped to the caller."""
    return FileService(
        user_id=str(user.id),
        sandbox_root=cfg.sandbox_root,
        max_upload_mb=cfg.max_upload_mb,
    )


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------


@router.get("")
async def list_files(
    path: str = Query("", description="Path relative to the user root"),
    user: user_schemas.User = Depends(get_current_terminal_user),
    fs: FileService = Depends(get_file_service),
) -> list[dict]:
    """List the contents of a directory inside the caller's sandbox."""
    try:
        return fs.list_dir(path)
    except PathEscapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except FileNotFoundErrorInSandbox as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FileServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/upload")
async def upload_file(
    path: str = Query(
        "", description="Target directory relative to user root"
    ),
    file: UploadFile = ...,
    user: user_schemas.User = Depends(get_current_terminal_user),
    fs: FileService = Depends(get_file_service),
    cfg: TerminalConfig = Depends(get_terminal_config),
) -> dict:
    """Upload a single file into the caller's sandbox."""
    auditor = TerminalAuditor(cfg)
    content = await file.read()
    try:
        written = fs.save_upload(path, file.filename or "", content)
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except PathEscapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except FileNotFoundErrorInSandbox as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FileServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    auditor.file_operation(
        user_id=str(user.id),
        user_name=user.user_name,
        operation="upload",
        path=str(written),
        size_bytes=len(content),
    )
    return {
        "path": str(written.relative_to(fs.root)),
        "size": len(content),
    }


@router.get("/download")
async def download_file(
    path: str = Query(..., description="File path relative to user root"),
    user: user_schemas.User = Depends(get_current_terminal_user),
    fs: FileService = Depends(get_file_service),
) -> Response:
    """Download a single file from the caller's sandbox."""
    try:
        data = fs.read_file(path)
        # Public helper performs the same path-escape validation as
        # ``_resolve`` while keeping the private method encapsulated.
        filename = fs.resolve_filename(path)
    except PathEscapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except FileNotFoundErrorInSandbox as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FileServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    quoted = urllib.parse.quote(filename)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (f"attachment; filename*=UTF-8''{quoted}"),
            "Content-Length": str(len(data)),
        },
    )


@router.delete("")
async def delete_file(
    path: str = Query(..., description="File path relative to user root"),
    user: user_schemas.User = Depends(get_current_terminal_user),
    fs: FileService = Depends(get_file_service),
    cfg: TerminalConfig = Depends(get_terminal_config),
) -> dict:
    """Delete a file or an empty directory inside the caller's sandbox."""
    auditor = TerminalAuditor(cfg)
    try:
        fs.delete(path)
    except PathEscapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except FileNotFoundErrorInSandbox as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except NotEmptyDirectoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except FileServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    auditor.file_operation(
        user_id=str(user.id),
        user_name=user.user_name,
        operation="delete",
        path=path,
    )
    return {"deleted": path}
