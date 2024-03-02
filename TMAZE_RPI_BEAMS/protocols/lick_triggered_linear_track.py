from statemachine import State
from PyQt5.QtCore import  QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
import numpy as np
from pyBehavior.protocols import Protocol
import json


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
        self.tracker = linear_tracker()
        self.tracker.show()
        for i in self.parent.reward_modules:
            idx = self.parent.reward_modules[i].trigger_mode.findText("No Trigger")
            self.parent.reward_modules[i].trigger_mode.setCurrentIndex(idx)
        self.lick_action_map = {"a": self.lickA, "b": self.lickB}
        self.licks = {"a": 0, "b": 0}

    def increment_lap(self):
        self.tracker.tot_laps_n += 1
        self.tracker.tot_laps.setText(f"Total Laps: {self.tracker.tot_laps_n//2}")
        self.tracker.current_trial_start = datetime.now()

    def increment_a(self):
        self.licks["a"] += 1
        self.licks["b"] = 0
    
    def increment_b(self):
        self.licks["b"] += 1
        self.licks["a"] = 0

    def sub_thresh(self):
        arm = self.current_state.id[0]
        return (self.licks[arm] + 1) < float(self.parent.reward_modules[arm].reward_thresh.text())

    def handle_input(self, sm_input):
        if sm_input['type'] == "lick":
            if sm_input['arm'] in self.lick_action_map:
                for _ in range(sm_input["amt"]):
                    self.lick_action_map[sm_input["arm"]]()

    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, False, force = True, wait = False)
        self.tracker.tot_rewards_n += 1
        self.tracker.tot_rewards.setText(f"Total # Rewards: {self.tracker.tot_rewards_n}")
        self.tracker.total_reward_amt += float(self.parent.reward_modules[arm].amt.text())
        self.tracker.total_reward.setText(f"Total Reward: {self.tracker.total_reward_amt:.2f} mL")


class linear_tracker(QMainWindow):
    def __init__(self):
        super(linear_tracker, self).__init__()
        self.layout = QVBoxLayout()

        self.tot_laps = QLabel(f"Total Laps: 0")
        self.tot_laps_n = 0   

        self.tot_rewards = QLabel(f"Total # Rewards: 0")
        self.tot_rewards_n = 0

        self.total_reward = QLabel(f"Total Reward: 0.00 mL")
        self.total_reward_amt = 0

        self.exp_time = QLabel(f"Experiment Time: 0.00 s")
        self.current_trial_time = QLabel(f"Current Trial Time: 0.00 s")

        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        self.layout.addWidget(self.tot_laps)
        self.layout.addWidget(self.tot_rewards)
        self.layout.addWidget(self.total_reward)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.current_trial_time)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")
        self.current_trial_time.setText(f"Current Trial Time: {(datetime.now() - self.current_trial_start).total_seconds():.2f} s")

        

