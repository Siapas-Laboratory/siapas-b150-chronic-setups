from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
from pyBehavior.protocols import Protocol


class lick_for_reward_prog(Protocol):

    waiting = State("waiting", initial=True)
    licking= State("licking")

    lick =  (  waiting.to(licking, before = "increment_lick")
               | licking.to(licking, cond = "sub_thresh", before = "increment_lick")
               | licking.to(waiting, before = "increment_lick", after = "deliver_reward")
    )

    def __init__(self, parent):
        super(lick_for_reward_prog, self).__init__(parent)
        self.tracker = tracker()
        self.tracker.show()
        for i in self.parent.reward_modules:
            idx = self.parent.reward_modules[i].trigger_mode.findText("No Trigger")
            self.parent.reward_modules[i].trigger_mode.setCurrentIndex(idx)

    def increment_licks(self):
        self.tracker.increment_licks()

    def sub_thresh(self):
        return  (self.tracker.licks + 1) < self.tracker.thresh

    def handle_input(self, sm_input):
        if sm_input['type'] == "lick":
            for _ in range(sm_input["data"]):
                self.lick()

    def deliver_reward(self):
        self.parent.trigger_reward('a', False, force = False, wait = True)
        self.tracker.reset_licks()
        self.tracker.increment_reward(float(self.parent.reward_modules['a'].amt.text()))
        self.tracker.update_thresh()


class tracker(QMainWindow):
    def __init__(self, thresh_update_interval = 10):
        super(tracker, self).__init__()
        self.layout = QVBoxLayout()

        self.thresh = 0
        self.tresh_label = QLabel(f"Current Threshold: 0")


        self.tot_rewards = QLabel(f"Total # Rewards: 0")
        self.tot_rewards_n = 0

        self.total_reward = QLabel(f"Total Reward: 0.00 mL")
        self.total_reward_amt = 0

        self.exp_time = QLabel(f"Experiment Time: 0.00 s")
        self.current_trial_time = QLabel(f"Current Trial Time: 0.00 s")

        self.licks = 0
        self.lick_tracker = QLabel(f"Current Trial Lick Count: 0")

        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        self.layout.addWidget(self.thresh_label)
        self.layout.addWidget(self.tot_rewards)
        self.layout.addWidget(self.total_reward)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.current_trial_time)
        self.layout.addWidget(self.lick_tracker)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")
        self.current_trial_time.setText(f"Current Trial Time: {(datetime.now() - self.current_trial_start).total_seconds():.2f} s")

    def increment_reward(self, amount):
        self.current_trial_start = datetime.now()
        self.tot_rewards_n += 1
        self.tot_rewards.setText(f"Total # Rewards: {self.tot_rewards_n}")
        self.total_reward_amt += amount
        self.total_reward.setText(f"Total Reward: {self.total_reward_amt:.2f} mL")

    def reset_licks(self):
        self.licks = 0
        self.lick_tracker.setText(f"Current Trial Lick Count: {self.licks}")

    def increment_licks(self):
        self.licks += 1
        self.lick_tracker.setText(f"Current Trial Lick Count: {self.licks}")

    def update_thresh(self):
        if self.tot_rewards_n % self.update_interval:
            self.thresh += 1
            self.thresh_label.setText(f"Current Threshold: {self.thresh}")


