from fastapi import HTTPException, Request, status
from orjson import JSONDecodeError


async def formHandler(request: Request):
    content_type = request.headers.get("content-type")
    if content_type == None:
        raise HTTPException(
            detail="content type not provided", status_code=status.HTTP_400_BAD_REQUEST
        )
    elif content_type == "application/json":
        try:
            return await request.json()
        except JSONDecodeError:

            raise HTTPException(
                detail="".format(JSONDecodeError),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    elif content_type == "application/x-www-form-urlencoded" or content_type.startswith(
        "multipart/form-data"
    ):
        try:
            return await request.form()
        except Exception:
            raise HTTPException(
                detail="".format(Exception),
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
