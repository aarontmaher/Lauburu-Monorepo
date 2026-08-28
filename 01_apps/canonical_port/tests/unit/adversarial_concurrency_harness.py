import os
import sys
import time
import tempfile
import multiprocessing
from pathlib import Path

# Add project root
sys.path.insert(0, os.path.abspath('.'))

from backend.devils_lock_governor import DevilsLockGovernor

def run_agent_process(lock_dir: str, agent_id: str, queue: multiprocessing.Queue, barrier: multiprocessing.Barrier):
    gov = DevilsLockGovernor(lock_dir=lock_dir)
    try:
        barrier.wait(timeout=5)
    except Exception:
        pass

    start_t = time.time()
    acquired = gov.acquire_subagent_lock(agent_id, f'task_{agent_id}')
    duration = time.time() - start_t

    if acquired:
        time.sleep(0.3)
        active = gov.get_active_subagent()
        active_id = active.subagent_id if active else None
        gov.release_subagent_lock(agent_id)
        queue.put({'agent_id': agent_id, 'acquired': True, 'duration': duration, 'active_id_match': (active_id == agent_id)})
    else:
        queue.put({'agent_id': agent_id, 'acquired': False, 'duration': duration, 'active_id_match': None})

def main():
    print('[Test 6] Running Multi-Process High-Concurrency Stampede (10 Processes)...')
    with tempfile.TemporaryDirectory() as td:
        lock_dir = str(Path(td) / 'stampede_locks')
        num_procs = 10
        queue = multiprocessing.Queue()
        barrier = multiprocessing.Barrier(num_procs)

        procs = []
        for i in range(num_procs):
            p = multiprocessing.Process(
                target=run_agent_process,
                args=(lock_dir, f'agent_proc_{i}', queue, barrier)
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join(timeout=10)

        results = []
        while not queue.empty():
            results.append(queue.get())

        print(f'  Collected {len(results)} process results:')
        acquired_list = [r for r in results if r["acquired"]]
        rejected_list = [r for r in results if not r["acquired"]]

        print(f'  Acquired count: {len(acquired_list)}')
        print(f'  Rejected count: {len(rejected_list)}')
        for r in acquired_list:
            print(f'    Winner: {r["agent_id"]} (Lock match: {r["active_id_match"]})')

        assert len(acquired_list) == 1, f'Expected exactly 1 winner, got {len(acquired_list)}'
        assert len(rejected_list) == num_procs - 1, f'Expected {num_procs - 1} rejections'
        assert acquired_list[0]["active_id_match"] is True, 'Active subagent did not match winner'

        # Verify lock dir is now clean and available
        final_gov = DevilsLockGovernor(lock_dir=lock_dir)
        assert final_gov.check_resource_cap() is True, 'Resource cap should be available after winner released'
        assert final_gov.acquire_subagent_lock('final_checker', 'check_task') is True, 'Final acquisition should succeed'
        final_gov.release_subagent_lock('final_checker')

        print('  -> PASS: Multi-process stampede strictly enforced single-agent exclusivity.')

if __name__ == '__main__':
    main()
