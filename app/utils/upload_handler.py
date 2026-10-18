import os
from datetime import datetime
from typing import Any

from fastapi import UploadFile

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

MEDIA_DIR: str = os.path.join(BASE_DIR, "uploads")
if not MEDIA_DIR:
    os.mkdir(MEDIA_DIR)

date: str = datetime.now().strftime("%m%d%Y%H%M%S")


async def uploadHandler(
    fil: UploadFile | Any,
    user_id: str,
):
    
    filename = "{}_{}{}".format(
        os.path.splitext(fil.filename)[0], date, os.path.splitext(fil.filename)[-1]  # type: ignore
    )
    file_path: str = os.path.join(MEDIA_DIR, filename)
    with open(filename, "wb") as f:
        filed = await fil.read()
        f.write(filed)

    return filename


async def deleteHandler(filename: str):
    file_path = os.path.join(MEDIA_DIR, filename)
    os.remove(path=file_path)
    return "{} is deleted successfully".format(filename)
