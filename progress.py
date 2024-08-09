import time
import math

def humanbytes(size):
    if not size:
        return "0B"
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{math.floor(size)} {Dic_powerN[n]}B"

async def progress(current, total, message, start_time, description=""):
    now = time.time()
    diff = now - start_time
    if diff >= 1:  # Update every second
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff)
        time_to_completion = round((total - current) / speed)
        estimated_total_time = elapsed_time + time_to_completion
        
        progress_str = "[{0}{1}] {2}%".format(
            ''.join(["█" for i in range(math.floor(percentage / 10))]),
            ''.join(["░" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2)
        )

        tmp = (f"{description}\n"
               f"{progress_str}\n"
               f"{humanbytes(current)} of {humanbytes(total)} @ {humanbytes(speed)}/s\n"
               f"Time Elapsed: {elapsed_time}s | Time Left: {time_to_completion}s")

        try:
            if message and message.chat and message.id:
                await message.edit_text(text=tmp)
        except Exception as e:
            print(f"Error updating progress: {e}")

def time_formatter(seconds):
    result = ""
    v_m = seconds // 60
    v_s = seconds % 60
    v_h = v_m // 60
    v_m = v_m % 60
    v_d = v_h // 24
    v_h = v_h % 24
    if v_d != 0:
        result += f"{v_d}d"
    if v_h != 0:
        result += f"{v_h}h"
    if v_m != 0:
        result += f"{v_m}m"
    if v_s != 0:
        result += f"{v_s}s"
    return result
