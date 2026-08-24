from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import cadquery as cq


class ModelRunError(RuntimeError):
    pass


def run_model(revision_dir: Path, python_path: Path, timeout_seconds: int = 240) -> None:
    model_path = revision_dir / "model.py"
    if not model_path.exists():
        raise ModelRunError("缺少 model.py。")

    output_dir = (revision_dir / "output").resolve()
    expected_parent = revision_dir.resolve()
    if output_dir.parent != expected_parent:
        raise ModelRunError("输出目录不安全。")
    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        result = subprocess.run(
            [str(python_path.expanduser().absolute()), str(model_path)],
            cwd=revision_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ModelRunError(f"CadQuery 导出超过 {timeout_seconds} 秒。") from exc

    log = f"STDOUT\n{result.stdout}\n\nSTDERR\n{result.stderr}"
    (revision_dir / "model-run.log").write_text(log, encoding="utf-8")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "没有错误详情。"
        raise ModelRunError(f"CadQuery 执行失败：{detail[-2500:]}")


def validate_outputs(revision_dir: Path) -> dict[str, Any]:
    output_dir = revision_dir / "output"
    step_path = output_dir / "model.step"
    stl_path = output_dir / "model.stl"
    for path in (step_path, stl_path):
        if not path.is_file() or path.stat().st_size < 100:
            raise ModelRunError(f"缺少有效的 {path.name}。")

    try:
        imported = cq.importers.importStep(str(step_path))
        solids = []
        for shape in imported.objects:
            solids.extend(shape.Solids())
    except Exception as exc:  # CadQuery/OCP exposes several exception types.
        raise ModelRunError(f"STEP 无法重新导入：{exc}") from exc

    if not solids:
        raise ModelRunError("STEP 中没有检测到实体。")
    if not all(solid.isValid() for solid in solids):
        raise ModelRunError("STEP 包含无效实体。")

    volume = sum(float(solid.Volume()) for solid in solids)
    boxes = [solid.BoundingBox() for solid in solids]
    bounds = {
        "x_min": min(box.xmin for box in boxes),
        "x_max": max(box.xmax for box in boxes),
        "y_min": min(box.ymin for box in boxes),
        "y_max": max(box.ymax for box in boxes),
        "z_min": min(box.zmin for box in boxes),
        "z_max": max(box.zmax for box in boxes),
    }
    size = {
        "x": bounds["x_max"] - bounds["x_min"],
        "y": bounds["y_max"] - bounds["y_min"],
        "z": bounds["z_max"] - bounds["z_min"],
    }
    values = [volume, *size.values()]
    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ModelRunError("模型体积或包围盒尺寸无效。")

    validation = {
        "shape_valid": True,
        "solid_count": len(solids),
        "volume_mm3": round(volume, 3),
        "bounding_box_mm": {axis: round(value, 3) for axis, value in size.items()},
        "step_bytes": step_path.stat().st_size,
        "stl_bytes": stl_path.stat().st_size,
    }
    (revision_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return validation
