from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtGui import  QDoubleValidator
from datetime import datetime
from pyBehavior.protocols import Protocol
from pyBehavior.gui import LoggableLineEdit
import random


class lick_triggered_linear_track(Protocol):

    sleep = State("sleep", initial=True)
    a_licking= State("a_licking")
    a_waiting = State("a_waiting")
    b_licking= State("b_licking")
    b_waiting = State("b_waiting")


    lickA =  ( sleep.to(a_licking, after = "increment_lap", before = "increment_a") 
               | a_waiting.to(a_licking,  before = "increment_a")
               | a_licking.to.itself(cond = "sub_thresh", before = "increment_a") 
               | a_licking.to(b_waiting, before = "increment_a", on = "deliver_reward", after = "increment_lap")
               | b_licking.to(a_licking, after = "increment_lap", before = "increment_a")
               | b_waiting.to.itself()
    )

    lickB =  ( sleep.to(b_licking, before = "increment_b", after = "increment_lap") 
               | b_waiting.to(b_licking, before = "increment_b")
               | b_licking.to.itself(cond = "sub_thresh", before = "increment_b") 
               | b_licking.to(a_waiting, before = "increment_b", on = "deliver_reward", after = "increment_lap")
               | a_licking.to(b_licking, before = "increment_b", after = "increment_lap")
               | a_waiting.to.itself()
    )

    def __init__(self, parent):
        super(lick_triggered_linear_track, self).__init__(parent)
        self.tracker = linear_tracker(self)
        self.tracker.show()
        self.lick_action_map = {"a": self.lickA, "b": self.lickB}

    def increment_lap(self):
        self.tracker.increment_lap()

    def increment_a(self):
        self.tracker.increment_a()
    
    def increment_b(self):
        self.tracker.increment_b()

    def sub_thresh(self):
        arm = self.current_state.id[0]
        return (self.tracker.licks[arm] + 1) < float(self.tracker.thresh[arm].text())

    def handle_input(self, sm_input):
        if sm_input['type'] == "lick":
            if sm_input['metadata']['arm'] in self.lick_action_map:
                for _ in range(sm_input["data"]):
                    self.lick_action_map[sm_input["metadata"]["arm"]]()

    def deliver_reward(self):
        arm = self.current_state.id[0]
        if random.uniform(0,1) < float(self.tracker.probe_prob.text()):
            self.parent.log("probe trial", event_line = self.parent.event_line)
            amt = 0
        else:
            self.parent.log("rewarded trial", event_line = self.parent.event_line)
            amt = float(self.tracker.reward_amount.text())
        self.parent.trigger_reward(arm, amt, force = False, enqueue = True)
        self.tracker.reset_licks()
        self.tracker.increment_reward(amount=amt)


class linear_tracker(QMainWindow):
    def __init__(self, parent):
        super(linear_tracker, self).__init__()
        self.layout = QVBoxLayout()
        self.parent = parent
        reward_amount_layout = QHBoxLayout()
        reward_amount_label = QLabel("Reward Amount (mL): ")
        self.reward_amount = LoggableLineEdit("reward_amount", self.parent.parent)
        self.reward_amount.setText("0.2")
        self.reward_amount.setValidator(QDoubleValidator())
        reward_amount_layout.addWidget(reward_amount_label)
        reward_amount_layout.addWidget(self.reward_amount)

        probe_prob_layout = QHBoxLayout()
        probe_prob_label = QLabel("Probe Probability")
        self.probe_prob = LoggableLineEdit("probe_prob", self.parent.parent)
        self.probe_prob.setText("0.0")
        self.probe_prob.setValidator(QDoubleValidator())
        probe_prob_layout.addWidget(probe_prob_label)
        probe_prob_layout.addWidget(self.probe_prob)

        self.thresh = {}
        a_thresh_layout = QHBoxLayout()
        a_thresh_label = QLabel("Current Lick Threshold A: ")
        self.thresh['a'] = LoggableLineEdit("lick_thresh_a", self.parent.parent)
        self.thresh['a'].setValidator(QDoubleValidator())
        self.thresh['a'].setText('3')
        a_thresh_layout.addWidget(a_thresh_label)
        a_thresh_layout.addWidget(self.thresh['a'])

        b_thresh_layout = QHBoxLayout()
        b_thresh_label = QLabel("Current Lick Threshold B: ")
        self.thresh['b'] = LoggableLineEdit("lick_thresh_b", self.parent.parent)
        self.thresh['b'].setValidator(QDoubleValidator())
        self.thresh['b'].setText('5')
        b_thresh_layout.addWidget(b_thresh_label)
        b_thresh_layout.addWidget(self.thresh['b'])

        self.tot_laps = QLabel(f"Total Laps: 0")
        self.tot_laps_n = 0   

        self.tot_rewards = QLabel(f"Total # Rewards: 0")
        self.tot_rewards_n = 0

        self.total_reward = QLabel(f"Total Reward: 0.00 mL")
        self.total_reward_amt = 0

        self.exp_time = QLabel(f"Experiment Time: 0.00 s")
        self.current_trial_time = QLabel(f"Current Trial Time: 0.00 s")

        self.licks = {"a": 0, "b": 0}
        self.lick_a_tracker = QLabel(f"Current A Lick Count: 0")
        self.lick_b_tracker = QLabel(f"Current B Lick Count: 0")

        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        self.layout.addWidget(self.tot_laps)
        self.layout.addWidget(self.tot_rewards)
        self.layout.addLayout(reward_amount_layout)
        self.layout.addWidget(self.total_reward)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.current_trial_time)
        self.layout.addLayout(a_thresh_layout)
        self.layout.addWidget(self.lick_a_tracker)
        self.layout.addLayout(b_thresh_layout)
        self.layout.addWidget(self.lick_b_tracker)
        self.layout.addLayout(probe_prob_layout)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")
        self.current_trial_time.setText(f"Current Trial Time: {(datetime.now() - self.current_trial_start).total_seconds():.2f} s")

    def increment_lap(self):
        self.tot_laps_n += 1
        if self.tot_laps_n%2 == 0:
            self.current_trial_start = datetime.now()
            self.tot_laps.setText(f"Total Laps: {self.tot_laps_n//2}")

    def increment_reward(self, amount = None):
        if not amount:
            amount = float(self.reward_amount.text())
        self.tot_rewards_n += 1
        self.tot_rewards.setText(f"Total # Rewards: {self.tot_rewards_n}")
        self.total_reward_amt += amount
        self.total_reward.setText(f"Total Reward: {self.total_reward_amt:.2f} mL")

    def increment_a(self):
        self.licks["a"] += 1
        self.licks["b"] = 0
        self.update_licks()
        
    def increment_b(self):
        self.licks["b"] += 1
        self.licks["a"] = 0
        self.update_licks()

    def reset_licks(self):
        self.licks["a"] = 0
        self.licks["b"] = 0
        self.update_licks()

    def update_licks(self):
        self.lick_a_tracker.setText(f"Current A Lick Count: {self.licks['a']}")
        self.lick_a_tracker.setText(f"Current B Lick Count: {self.licks['b']}")

        

