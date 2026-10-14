from storesignal.detection.emerging import run as detect
from storesignal.fusion.incidents import run as fuse
from storesignal.alerts.generate import run as alerts
from storesignal.policy.guardrail import run as policy
if __name__ == "__main__":
    policy()
    detect()
    fuse()
    alerts()
