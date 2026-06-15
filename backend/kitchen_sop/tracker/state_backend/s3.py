"""S3 state backend using boto3."""

import json
import logging
import os
from typing import List, Optional

from ..models import Checkpoint, RunRecord
from .base import StateBackend

logger = logging.getLogger("kitchen_agent")


class S3StateBackend(StateBackend):
    """S3 持久化后端."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        prefix: str = "kitchen_sop",
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
    ):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError(
                "S3 backend requires boto3. Install it: pip install boto3"
            ) from e

        self.bucket = bucket or os.environ.get("KITCHEN_S3_BUCKET")
        self.prefix = prefix or os.environ.get("KITCHEN_S3_PREFIX", "kitchen_sop")
        if not self.bucket:
            raise RuntimeError(
                "S3 bucket is required. Set KITCHEN_S3_BUCKET or pass bucket=."
            )

        endpoint = endpoint_url or os.environ.get("KITCHEN_S3_ENDPOINT_URL")
        region = region or os.environ.get("AWS_REGION")
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )

    def _run_key(self, run_id: str) -> str:
        return f"{self.prefix}/runs/{run_id}.json"

    def _cp_key(self, run_id: str, checkpoint_id: str) -> str:
        return f"{self.prefix}/checkpoints/{run_id}_{checkpoint_id}.json"

    async def save_run(self, run: RunRecord) -> None:
        key = self._run_key(run.run_id)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(run.to_dict(), ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.debug(f"Run saved to S3: {key}")

    async def load_run(self, run_id: str) -> Optional[RunRecord]:
        key = self._run_key(run_id)
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            return RunRecord.from_dict(json.loads(resp["Body"].read().decode("utf-8")))
        except Exception as e:
            logger.debug(f"S3 load_run failed: {e}")
            return None

    async def list_runs(self, limit: int = 20) -> List[RunRecord]:
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}/runs/", MaxKeys=limit * 2
            )
            contents = resp.get("Contents", [])
            items = sorted(contents, key=lambda x: x["LastModified"], reverse=True)
            records = []
            for item in items[:limit]:
                try:
                    resp2 = self.s3.get_object(Bucket=self.bucket, Key=item["Key"])
                    records.append(
                        RunRecord.from_dict(json.loads(resp2["Body"].read().decode("utf-8")))
                    )
                except Exception:
                    pass
            return records
        except Exception as e:
            logger.warning(f"S3 list_runs failed: {e}")
            return []

    async def delete_run(self, run_id: str) -> None:
        key = self._run_key(run_id)
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            logger.warning(f"S3 delete_run failed: {e}")

    async def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        key = self._cp_key(checkpoint.run_id, checkpoint.checkpoint_id)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.debug(f"Checkpoint saved to S3: {key}")
        return checkpoint

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}/checkpoints/"
            )
            for item in resp.get("Contents", []):
                if item["Key"].endswith(f"_{checkpoint_id}.json"):
                    resp2 = self.s3.get_object(Bucket=self.bucket, Key=item["Key"])
                    return Checkpoint.from_dict(
                        json.loads(resp2["Body"].read().decode("utf-8"))
                    )
        except Exception as e:
            logger.debug(f"S3 load_checkpoint failed: {e}")
        return None

    async def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        cps = []
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}/checkpoints/{run_id}_"
            )
            for item in resp.get("Contents", []):
                try:
                    resp2 = self.s3.get_object(Bucket=self.bucket, Key=item["Key"])
                    cps.append(
                        Checkpoint.from_dict(
                            json.loads(resp2["Body"].read().decode("utf-8"))
                        )
                    )
                except Exception:
                    pass
            cps.sort(key=lambda c: c.created_at)
        except Exception as e:
            logger.warning(f"S3 list_checkpoints failed: {e}")
        return cps

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}/checkpoints/"
            )
            for item in resp.get("Contents", []):
                if item["Key"].endswith(f"_{checkpoint_id}.json"):
                    self.s3.delete_object(Bucket=self.bucket, Key=item["Key"])
        except Exception as e:
            logger.warning(f"S3 delete_checkpoint failed: {e}")

    async def delete_run_checkpoints(self, run_id: str) -> None:
        try:
            resp = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{self.prefix}/checkpoints/{run_id}_"
            )
            for item in resp.get("Contents", []):
                self.s3.delete_object(Bucket=self.bucket, Key=item["Key"])
        except Exception as e:
            logger.warning(f"S3 delete_run_checkpoints failed: {e}")
