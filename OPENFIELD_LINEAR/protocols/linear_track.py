from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtGui import  QDoubleValidator
from datetime import datetime
import numpy as np
from pyBehavior.protocols import Protocol
from pyBehavior.gui import LoggableLineEdit


class linear_track(Protocol):

    sleep = State("sleep", initial=True)
    a_reward= State("a_reward")
    b_reward= State("b_reward")

    zoneA =  ( sleep.to(a_reward,  after = "deliver_reward") 
               | b_reward.to(a_reward,  after = "deliver_reward") 
               | a_reward.to.itself() 
    )


    zoneB =  ( sleep.to(b_reward,  after = "deliver_reward") 
               | a_reward.to(b_reward,  after = "deliver_reward") 
               | b_reward.to.itself() 
    )

    def __init__(self, parent):
        super(linear_track, self).__init__(parent)
        self.tracker = linear_tracker()
        self.tracker.show()
        self.zoneA_span = np.array([[1400, 1900], # x span of zone A
                                    [800, 1600]])  # y span of zone A
        self.zoneB_span = np.array([[0, 500], # x span of zone B
                                    [800, 1600]]) # y span of zone B
        
        
    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.log(f"arm {arm} correct")
        self.parent.trigger_reward(arm, float(self.tracker.reward_amount.text()),
                                   force = False, enqueue = True)
        self.tracker.increment_lap()
        self.tracker.increment_reward()


    def handle_input(self, sm_input):
        if sm_input["type"] == "pos":
            pos = sm_input["pos"]
            if (( self.zoneA_span[0,0] <= pos[0]) and (pos[0] <= self.zoneA_span[0,1]) 
                and (self.zoneA_span[1,0] <= pos[1]) and (pos[1] <= self.zoneA_span[1,1])):
                self.zoneA()
            elif (( self.zoneB_span[0,0] <= pos[0]) and (pos[0] <= self.zoneB_span[0,1]) 
                and (self.zoneB_span[1,0] <= pos[1]) and (pos[1] <= self.zoneB_span[1,1])):
                self.zoneB()

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
        self.layout.addLayout(reward_amount_layout)
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
        

