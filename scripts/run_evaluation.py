from storesignal.evaluation.run_eval import run as ev
from storesignal.replay.simulator import run as replay
from storesignal.brief.generator import run as brief
if __name__ == "__main__":
    ev()
    replay()
    brief()
