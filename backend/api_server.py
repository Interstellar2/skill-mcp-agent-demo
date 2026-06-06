"""Uvicorn 入口脚本."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("kitchen_sop.api.main:app", host="0.0.0.0", port=8000, reload=True)
