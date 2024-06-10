import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional


def parallel_exec(
    fn: Callable,
    list_of_kwargs: List[dict],
    max_workers: Optional[int] = None,
    jitter: float = 0.0,
) -> list:
    """
    Executes a given function `fn` in parallel, using multiple threads, on a list of argument tuples.
    The function limits the number of concurrent executions to `max_workers` and processes tasks in chunks,
    pausing between each chunk to avoid hitting rate limits or quotas.

    Args:
    - fn (Callable): The function to execute in parallel.
    - list_of_kwargs (list): A list of dicts, where each dict contains arguments for a single call to `fn`.
    - max_workers (int, optional): The maximum number of threads that can be used to execute the tasks
      concurrently.
    - jitter (float, optional): Wait for jitter * random.random() before submitting the next job.

    Returns:
    - A list containing the results of the function calls. The order of the results corresponds to the order
      the tasks were completed, which may not necessarily be the same as the order of `list_of_kwargs`.

    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Get the tasks for the current chunk
        futures = []
        for kwargs in list_of_kwargs:
            futures.append(executor.submit(fn, **kwargs))
            if jitter > 0.0:
                time.sleep(jitter * random.random())
        for future in as_completed(futures):
            results.append(future.result())
    return results


# for debug
def serial_exec(fn: Callable, list_of_kwargs: List[dict]) -> List[Any]:
    results = []
    for kwargs in list_of_kwargs:
        result = fn(**kwargs)
        results.append(result)
    return results
