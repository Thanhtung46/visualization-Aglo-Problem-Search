import random


GOAL_STATE = (1, 2, 3, 4, 5, 6, 7, 8, 0)
DEFAULT_INITIAL_STATE = (1, 2, 3, 4, 0, 5, 7, 8, 6) 


def is_solvable(state):
    nums = [n for n in state if n != 0]
    inversions = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] > nums[j]:
                inversions += 1
    return inversions % 2 == 0


def random_solvable_state(goal_state=GOAL_STATE):
    nums = list(range(9))
    while True:
        random.shuffle(nums)
        state = tuple(nums)
        if state != goal_state and is_solvable(state):
            return state


def get_neighbors(state):
    neighbors = []
    idx = state.index(0)
    r, c = idx // 3, idx % 3

    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < 3 and 0 <= nc < 3:
            n_idx = nr * 3 + nc
            lst = list(state)
            lst[idx], lst[n_idx] = lst[n_idx], lst[idx]
            neighbors.append(tuple(lst))
    return neighbors


def reconstruct_path(parent_map, end_state):
    path = []
    cur = end_state
    while cur is not None:
        path.append(cur)
        cur = parent_map.get(cur)
    path.reverse()
    return path
