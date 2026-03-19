"""GPU monitoring helpers."""

from __future__ import annotations

import logging
import subprocess

from config.constants import GPU_IDLE_THRESHOLD, GPU_INDEX


class GPUMonitor:
    """Reads local GPU utilization."""

    def is_idle(self, threshold: int = GPU_IDLE_THRESHOLD) -> bool:
        """Return True when the GPU utilization is below the threshold."""
        try:
            result = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                    "-i",
                    GPU_INDEX,
                ]
            )
            usage = int(result.decode().strip())
            logging.debug("GPU usage: %s%%", usage)
            return usage < threshold
        except subprocess.CalledProcessError as exc:
            logging.warning("nvidia-smi command failed, assuming GPU busy")
            return False
        except FileNotFoundError:
            logging.error("nvidia-smi not found; GPU monitoriing unavailable")
            return False
        except ValueError as exc:
            logging.warning("GPU utilization parse failed; assuming busy")
            return False
        except Exception as exc:
            logging.warning("Could not read GPU usage: %s; assuming busy", exc)
            return False
