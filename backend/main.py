import asyncio
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from ai_analyzer import AIAnalyzerError, analyze_resources
from auth import (
    AuthError,
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from azure_scanner import (
    AzureCLIError,
    AzureCLINotInstalledError,
    AzureCLINotLoggedInError,
    ResourceGroupNotFoundError,
    list_resource_groups,
    list_resources,
)
from db import (
    DatabaseError,
    complete_analysis,
    create_analysis,
    create_user,
    fail_analysis,
    get_analysis_for_user,
    get_user_by_email,
    get_user_history,
    init_db,
    serialize_analysis,
)
from progress import ProgressManager

load_dotenv()

progress_manager = ProgressManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except DatabaseError:
        pass
    yield


app = FastAPI(title="AI Cloud Cost Detective", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AnalyzeRequest(BaseModel):
    resource_group: str = Field(min_length=1)


def _handle_azure_error(exc: AzureCLIError) -> HTTPException:
    if isinstance(exc, AzureCLINotInstalledError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, AzureCLINotLoggedInError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, ResourceGroupNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def _auth_response(user: dict[str, Any]) -> dict[str, Any]:
    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"]},
    }


@app.post("/api/auth/signup")
def signup(body: SignupRequest) -> dict:
    try:
        existing = get_user_by_email(body.email)
        if existing:
            raise HTTPException(
                status_code=409, detail="Email already registered."
            )
        user = create_user(body.email, hash_password(body.password))
        return _auth_response(user)
    except AuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/auth/login")
def login(body: LoginRequest) -> dict:
    try:
        user = get_user_by_email(body.email)
        if user is None or not verify_password(
            body.password, user["password_hash"]
        ):
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        return _auth_response(user)
    except AuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _run_analysis(
    analysis_id: int, resource_group: str, user_id: int
) -> None:
    try:
        await progress_manager.send_progress(
            analysis_id, "Fetching resource groups..."
        )
        await asyncio.to_thread(list_resource_groups)

        await progress_manager.send_progress(
            analysis_id, f"Scanning resources in {resource_group}..."
        )
        resources = await asyncio.to_thread(list_resources, resource_group)

        await progress_manager.send_progress(
            analysis_id, "Analyzing costs with AI..."
        )
        analysis = await asyncio.to_thread(
            analyze_resources, resource_group, resources
        )

        await progress_manager.send_progress(
            analysis_id, "Storing results..."
        )
        full_result: dict[str, Any] = {
            "resource_group": resource_group,
            "resource_count": len(resources),
            "resources": resources,
            "analysis": analysis,
        }
        complete_analysis(
            analysis_id,
            resources_scanned=len(resources),
            issues_found=len(analysis.get("issues", [])),
            estimated_savings=analysis.get("estimated_savings", ""),
            analysis_result=full_result,
        )

        await progress_manager.send_progress(analysis_id, "Analysis complete")
    except AzureCLIError as exc:
        fail_analysis(analysis_id, str(exc))
        await progress_manager.send_progress(
            analysis_id, f"Analysis failed: {exc}"
        )
    except AIAnalyzerError as exc:
        fail_analysis(analysis_id, str(exc))
        await progress_manager.send_progress(
            analysis_id, f"Analysis failed: {exc}"
        )
    except Exception as exc:
        fail_analysis(analysis_id, str(exc))
        await progress_manager.send_progress(
            analysis_id, f"Analysis failed: {exc}"
        )


@app.get("/api/resource-groups")
def get_resource_groups(
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        groups = list_resource_groups()
    except AzureCLIError as exc:
        raise _handle_azure_error(exc) from exc
    return {"resource_groups": groups}


@app.post("/api/analyze")
async def analyze_resource_group(
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["user_id"]
    try:
        analysis_id = create_analysis(body.resource_group, user_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    background_tasks.add_task(
        _run_analysis, analysis_id, body.resource_group, user_id
    )
    return {
        "analysis_id": analysis_id,
        "resource_group": body.resource_group,
        "status": "in_progress",
    }


@app.get("/api/analyses/{analysis_id}")
def get_analysis_result(
    analysis_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        row = get_analysis_for_user(analysis_id, current_user["user_id"])
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return serialize_analysis(row)


@app.get("/api/history")
def get_history(current_user: dict = Depends(get_current_user)) -> dict:
    try:
        rows = get_user_history(current_user["user_id"])
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "history": [serialize_analysis(row) for row in rows],
    }


@app.websocket("/ws/progress/{analysis_id}")
async def analysis_progress(websocket: WebSocket, analysis_id: int) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        decode_access_token(token)
    except AuthError:
        await websocket.close(code=1008)
        return

    await progress_manager.connect(analysis_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_manager.disconnect(analysis_id, websocket)
    except Exception:
        await progress_manager.disconnect(analysis_id, websocket)
