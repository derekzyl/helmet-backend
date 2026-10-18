from fastapi import status
from fastapi.responses import JSONResponse

from app.app import init_app
from app.utils.crud.types_crud import response_message

app = init_app()


@app.get("/")
async def root():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_message(
            data="Welcome to FastAPI SQLAlchemy Starter",
            success_status=True,
            message="success",
        ),
    )


@app.get("/health")
async def health():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_message(
            data={"status": "healthy"},
            success_status=True,
            message="OK",
        ),
    )
