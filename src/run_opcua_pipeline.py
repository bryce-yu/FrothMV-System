import argparse
import asyncio
from pathlib import Path

from mv import MVConfig, FrothMVPipeline
from communication import FrothOPCUAServer


SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
}


def get_image_files(folder: Path):
    """Return supported image files in deterministic order."""

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


async def heartbeat_loop(opcua_server):
    """Update heartbeat once per second."""

    while True:
        await opcua_server.increment_heartbeat()
        await asyncio.sleep(1)


async def command_monitor(opcua_server):
    """
    Monitor CommandFromEAE and print changes.
    """

    previous_value = None

    while True:
        value = await opcua_server.read_command()

        if value != previous_value:
            print(f"CommandFromEAE changed: {value}")
            previous_value = value

        await asyncio.sleep(0.25)


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

    pipeline = FrothMVPipeline(config)

    # ---------------------------------------------------------
    # Start OPC-UA communication layer
    # ---------------------------------------------------------

    opcua_server = FrothOPCUAServer()

    await opcua_server.start()

    # Temporarily commented out two lines for heartbeat stopped but comms alive test
    heartbeat_task = asyncio.create_task(
        heartbeat_loop(opcua_server)
    )

    command_task = asyncio.create_task(
        command_monitor(opcua_server)
    )

    try:
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

                print(
                    f"[{index}/{len(image_files)}] "
                    f"{image_path.name}: "
                    f"count={metrics['bubble_count']}, "
                    f"ECD={metrics['mean_equivalent_diameter_px']:.3f}, "
                    f"time={metrics['processing_time_seconds']:.3f}s"
                )

            except Exception as exc:
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
        command_task.cancel()

        await opcua_server.stop()


def main():
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