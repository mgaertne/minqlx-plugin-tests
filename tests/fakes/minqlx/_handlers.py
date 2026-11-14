import queue
import sched

import minqlx

frame_tasks = sched.scheduler()
next_frame_tasks: queue.Queue = queue.Queue()


def handle_frame():
    """Runs what the real handler runs every server frame: scheduled tasks, the frame event, next_frame tasks."""
    frame_tasks.run(blocking=False)
    minqlx.EVENT_DISPATCHERS["frame"].dispatch()

    while not next_frame_tasks.empty():
        func, args, kwargs = next_frame_tasks.get(block=False)
        frame_tasks.enter(0, 1, func, args, kwargs)
