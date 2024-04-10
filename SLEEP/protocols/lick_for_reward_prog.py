from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QMainWindow,QHBoxLayout, QVBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtGui import  QDoubleValidator
from datetime import datetime
from pyBehavior.protocols import Protocol


class lick_for_reward_prog(Protocol):

    waiting = State("waiting", initial=True)
    licking= State("licking")

    lick =  (  waiting.to(licking, cond= ["armed","sub_thresh"], after = "increment_licks")
               | waiting.to(waiting, cond = ["armed"], before = "increment_licks", after = "deliver_reward")
               | waiting.to(waiting, before = "increment_licks", after = "reset_trial_licks")
               | licking.to(licking, cond = "sub_thresh", before = "increment_licks")
               | licking.to(waiting, before = "increment_licks", after = "deliver_reward")
    )

    def __init__(self, parent):
        super(lick_for_reward_prog, self).__init__(parent)
        self.tracker = tracker(self)
        self.tracker.show()
        self.parent.log(f"state machine started with reward_amount={self.tracker.reward_amount.text()}; update_interval={self.tracker.update_interval.text()}; timeout={self.tracker.timeout.text()}")

    def reset_trial_licks(self):
        self.tracker.reset_trial_licks()

    def armed(self):
        if self.tracker.last_lick:
            return (datetime.now() - self.tracker.last_lick).total_seconds() > float(self.tracker.timeout.text())
        else:
            return True
    
    def increment_licks(self):
        self.tracker.increment_licks()

    def sub_thresh(self):
        return (self.tracker.curr_trial_licks + 1) < self.tracker.thresh

    def handle_input(self, sm_input):
        if sm_input['type'] == "lick":
            for _ in range(sm_input["data"]):
                self.lick()

    def deliver_reward(self):
        amt =  float(self.tracker.reward_amount.text())
        self.parent.trigger_reward('a', amt, force = False, enqueue = True)
        self.tracker.increment_reward(amt)
        self.tracker.update_thresh()


class tracker(QMainWindow):
    def __init__(self, parent):
        super(tracker, self).__init__()

        self.parent = parent
        self.layout = QVBoxLayout()

        reward_amount_layout = QHBoxLayout()
        reward_amount_label = QLabel("Reward Amount (mL): ")
        self.reward_amount = QLineEdit()
        self.reward_amount.setText("0.2")
        self.reward_amount.setValidator(QDoubleValidator())
        reward_amount_layout.addWidget(reward_amount_label)
        reward_amount_layout.addWidget(self.reward_amount)
        self.reward_amount.editingFinished.connect(lambda: self.notify("reward_amount"))


        self.tot_rewards = QLabel(f"Total # Rewards: 0")
        self.tot_rewards_n = 0

        self.total_reward = QLabel(f"Total Reward: 0.00 mL")
        self.total_reward_amt = 0

        self.exp_time = QLabel(f"Experiment Time: 0.00 s")

        self.licks = 0
        self.lick_tracker = QLabel(f"Lick Count: 0")
        self.last_lick = None
        self.last_lick_tracker  = QLabel(f"Last lick: ")

        self.curr_trial_licks = 0
        self.curr_trial_tracker = QLabel(f"Current Trial Lick Count: {self.curr_trial_licks}")


        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Timeout (s): ")
        self.timeout = QLineEdit()
        self.timeout.setText(f"{5}")
        self.timeout.setValidator(QDoubleValidator())
        self.timeout.editingFinished.connect(lambda: self.notify("timeout"))
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout)

        self.thresh = 1
        self.thresh_label = QLabel(f"Current Threshold: {self.thresh}")

        update_layout = QHBoxLayout()
        update_label = QLabel("Update Interval")
        self.update_interval = QLineEdit()
        self.update_interval.setText(f"{10}")
        self.update_interval.setValidator(QDoubleValidator())
        self.update_interval.editingFinished.connect(lambda: self.notify("update_interval"))
        update_layout.addWidget(update_label)
        update_layout.addWidget(self.update_interval)

        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        self.layout.addLayout(reward_amount_layout)
        self.layout.addWidget(self.tot_rewards)
        self.layout.addWidget(self.total_reward)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.lick_tracker)
        self.layout.addWidget(self.curr_trial_tracker)
        self.layout.addWidget(self.last_lick_tracker)
        self.layout.addLayout(timeout_layout)
        self.layout.addWidget(self.thresh_label)
        self.layout.addLayout(update_layout)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def notify(self, param_name):
        self.parent.parent.log(f"{param_name} updated to {getattr(self,param_name).text()}")

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")

    def increment_reward(self, amount):
        self.current_trial_start = datetime.now()
        self.tot_rewards_n += 1
        self.tot_rewards.setText(f"Total # Rewards: {self.tot_rewards_n}")
        self.total_reward_amt += amount
        self.total_reward.setText(f"Total Reward: {self.total_reward_amt:.2f} mL")
        self.reset_trial_licks()
    
    def reset_trial_licks(self):
        self.curr_trial_licks = 0
        self.curr_trial_tracker.setText(f"Current Trial Lick Count: {self.curr_trial_licks}")

    def increment_licks(self):
        self.licks += 1
        self.curr_trial_licks += 1
        self.last_lick = datetime.now()
        self.lick_tracker.setText(f"Lick Count: {self.licks}")
        self.curr_trial_tracker.setText(f"Current Trial Lick Count: {self.curr_trial_licks}")
        self.last_lick_tracker.setText(f"Last lick: {datetime.now()}")        


    def update_thresh(self):
        if self.tot_rewards_n % float(self.update_interval.text()) == 0:
            self.thresh += 1
            self.thresh_label.setText(f"Current Threshold: {self.thresh}")


