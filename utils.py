import time

def progress_for_pyrogram(current, total, message, start_time):
    """
    Displays a progress bar for file downloads and uploads.

    Args:
        current (int): The current progress.
        total (int): The total size of the file.
        message (pyrogram.types.Message): The message object for updating progress.
        start_time (float): The time when the process started.
    """
    progress = int(current / total * 100)
    elapsed_time = time.time() - start_time
    if elapsed_time > 0:
        speed = current / elapsed_time
        remaining_time = (total - current) / speed if speed > 0 else 0
        estimated_time = int(remaining_time)

        progress_text = f"{progress}% - {current / (1024 * 1024):.2f}MB of {total / (1024 * 1024):.2f}MB - ETA {estimated_time // 60}m {estimated_time % 60}s"
    else:
        progress_text = f"{progress}% - {current / (1024 * 1024):.2f}MB of {total / (1024 * 1024):.2f}MB"

    message.edit_text(progress_text, disable_web_page_preview=True)
