import argparse
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mv import MVConfig, FrothMVPipeline
from communication import FrothOPCUAServer
from mv.model_integrity import verify_model_integrity

logger = logging.getLogger("froth_mv_pipeline")
result_logger = logging.getLogger("froth_mv_pipeline.results")

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
}


def get_image_files(folder: Path):
    """Return candidate input files in deterministic order."""

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
    )


async def heartbeat_loop(opcua_server):
    """Update heartbeat once per second."""

    while True:
        await opcua_server.increment_heartbeat()
        await asyncio.sleep(1)


async def main_async(args):
    project_root = Path(__file__).resolve().parents[1]

    image_folder = Path(args.folder)

    if not image_folder.exists():
        raise FileNotFoundError(
            f"Image folder not found: {image_folder}"
        )

    image_files = get_image_files(image_folder)

    if not image_files:
        raise RuntimeError(
            f"No supported images found in: {image_folder}"
        )

    # ---------------------------------------------------------
    # Create the already-validated MV pipeline
    # ---------------------------------------------------------

    config = MVConfig(
        model_path=project_root / "models" / "best.pt",
        confidence=0.15,
        image_size=640,
        max_detections=1000,
        minimum_contour_area=10.0,
    )

    # Configuration logging 
    logger.info("Model path: %s", config.model_path)
    logger.info(
        "MV configuration: confidence=%.2f, image_size=%d, "
        "max_detections=%d, minimum_contour_area=%.1f",
        config.confidence,
        config.image_size,
        config.max_detections,
        config.minimum_contour_area,
    )

    # Active input restrictions logging
    logger.info(
    "Input validation: allowed_extensions=%s, "
    "max_file_size_bytes=%d, expected_dimensions=%dx%d",
    config.allowed_image_extensions,
    config.max_image_file_size_bytes,
    config.expected_image_width,
    config.expected_image_height,
    )

    # ---------------------------------------------------------
    # Start OPC-UA communication layer
    # ---------------------------------------------------------

    opcua_server = FrothOPCUAServer()

    await opcua_server.start()

    logger.info("OPC-UA endpoint: %s", opcua_server.endpoint)
    logger.info(
        "OPC-UA security enabled: "
        "Security Policy=Aes256Sha256RsaPss, "
        "Message Security Mode=SignAndEncrypt, "
        "username/password required, anonymous access disabled"
    )

    # Comment out for heartbeat stop test
    heartbeat_task = asyncio.create_task(
        heartbeat_loop(opcua_server)
    )

    pipeline = None

    try:
        model_hash_path = project_root / "models" / "best.pt.sha256"

        try:
            verified_hash = verify_model_integrity(
                model_path=config.model_path,
                hash_path=model_hash_path,
            )

            print()
            print("Model integrity verified.")
            print(f"SHA-256: {verified_hash}")

            logger.info("Model SHA-256 verification passed")
            logger.info("Model SHA-256: %s", verified_hash)

            pipeline = FrothMVPipeline(config)

            print("FrothMV pipeline loaded successfully.")

            logger.info("FrothMV pipeline loaded successfully")

        except Exception as exc:
            logger.critical(
                "Model integrity or pipeline startup failed: %s",
                exc,
            )

            await opcua_server.update_pipeline_failure(
                f"STARTUP MODEL INTEGRITY FAILURE: {exc}"
            )

            print()
            print(f"Model integrity check failed: {exc}")
            print("Pipeline will not process images.")
            print("OPC-UA server remains available for diagnostics.")
            print("Press Ctrl+C to stop.")

            while True:
                await asyncio.sleep(1)

        print()
        print(f"Processing {len(image_files)} images...")
        print()

        for index, image_path in enumerate(image_files, start=1):

            try:
                # YOLO/OpenCV work is synchronous and relatively slow.
                # Run it in a worker thread so the OPC-UA server and
                # heartbeat remain responsive during inference.
                metrics = await asyncio.to_thread(
                    pipeline.process_image,
                    image_path,
                )

                # Communication layer only receives the result.
                await opcua_server.update_metrics(metrics)

                result_logger.info(
                    "Published MV result: file=%s, status=%s, "
                    "bubble_count=%d, processing_time_seconds=%.3f",
                    image_path.name,
                    metrics.get("status", "UNKNOWN"),
                    int(metrics.get("bubble_count", 0)),
                    float(metrics.get("processing_time_seconds", 0.0)),
                )

                print(
                    f"[{index}/{len(image_files)}] "
                    f"{image_path.name}: "
                    f"BubbleCount={metrics['bubble_count']}, "
                    f"MedianECD={metrics['median_equivalent_diameter_px']:.3f}, "
                    f"ECD_P10={metrics['ecd_p10_px']:.3f}, "
                    f"ECD_P90={metrics['ecd_p90_px']:.3f}, "
                    f"MeanCircularity={metrics['mean_circularity']:.3f}, "
                    f"ProcessingTime={metrics['processing_time_seconds']:.3f}s"
                )

            except Exception as exc:
                logger.error(
                    "Image processing rejected: file=%s, reason=%s",
                    image_path,
                    exc,
                )

                await opcua_server.update_pipeline_failure(
                    f"ERROR: {image_path.name}: {exc}"
                )

                print(
                    f"[{index}/{len(image_files)}] "
                    f"ERROR: {image_path.name}: {exc}"
                )

            if args.interval > 0:
                await asyncio.sleep(args.interval)

        print()
        print("Folder processing complete.")
        print()
        print(
            "OPC-UA server will remain running so values can "
            "be inspected in UaExpert."
        )
        print("Press Ctrl+C to stop.")

        # Keep final values and server available for inspection.
        while True:
            await asyncio.sleep(1)

    finally:
        heartbeat_task.cancel() # Also commented out for heartbeat stop test

        await opcua_server.stop()


def main():
    log_format = "%(asctime)s | %(levelname)s | %(message)s"

    logging.basicConfig(
        level=logging.WARNING,
        format=log_format,
    )

    log_directory = (
        Path(__file__).resolve().parents[1] / "logs"
    )
    log_directory.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_directory / "froth_mv_pipeline.log",
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))

    # The root handler retains application and asyncua warnings.
    logging.getLogger().addHandler(file_handler)

    # Per-image result records go only to the log file.
    result_logger.setLevel(logging.INFO)
    result_logger.handlers.clear()
    result_logger.addHandler(file_handler)
    result_logger.propagate = False

    logger.setLevel(logging.INFO)
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    logging.getLogger(
        "communication.opcua_server"
    ).setLevel(logging.INFO)
        
    parser = argparse.ArgumentParser(
        description=(
            "Process froth images and publish soft-sensor "
            "metrics through OPC-UA."
        )
    )

    parser.add_argument(
        "folder",
        help="Folder containing froth images.",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help=(
            "Delay in seconds between published image results "
            "(default: 2.0)."
        ),
    )

    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))

    except KeyboardInterrupt:
        print()
        print("Stopped by user.")

    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()