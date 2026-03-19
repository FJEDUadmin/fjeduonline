from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from adductomics_api.schemas import RStatisticsRequest, RStatisticsResponse


class RStatisticsRunner:
    """Executes R-based statistical summary scripts when available."""

    def __init__(self, rscript_binary: str, script_path: str, output_dir: str) -> None:
        self.rscript_binary = rscript_binary
        self.script_path = Path(script_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, payload: RStatisticsRequest) -> RStatisticsResponse:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_json = self.output_dir / f"r_stats_{payload.sample_id}_{timestamp}.json"
        output_report = self.output_dir / f"r_stats_{payload.sample_id}_{timestamp}.txt"

        output_json.write_text(
            json.dumps(payload.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        rscript_path = shutil.which(self.rscript_binary)
        if rscript_path is None:
            return RStatisticsResponse(
                status="skipped",
                message=(
                    f"Rscript binary '{self.rscript_binary}' not found. "
                    "Input payload was saved for later execution."
                ),
                output_path=str(output_json),
                script_path=str(self.script_path),
            )
        if not self.script_path.exists():
            return RStatisticsResponse(
                status="skipped",
                message="R module script path does not exist; payload saved only.",
                output_path=str(output_json),
                script_path=str(self.script_path),
            )

        cmd = [rscript_path, str(self.script_path), str(output_json), str(output_report)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return RStatisticsResponse(
                status="failed",
                message=f"R script execution failed: {proc.stderr.strip() or proc.stdout.strip()}",
                output_path=str(output_json),
                script_path=str(self.script_path),
            )

        return RStatisticsResponse(
            status="completed",
            message=proc.stdout.strip() or "R report generated.",
            output_path=str(output_report),
            script_path=str(self.script_path),
        )
