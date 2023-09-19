from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
import numpy as np
from pyBehavior.protocols import Protocol


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
        self.zoneA_span = np.array([[-100, 400], # x span of zone A
                                    [600, 1000]])  # y span of zone A
        self.zoneB_span = np.array([[1100, 1600], # x span of zone B
                                    [600, 1000]]) # y span of zone B
        
    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.log(f"arm {arm} correct")
        self.parent.trigger_reward(arm, False)
        self.tracker.current_trial_start = datetime.now()
        self.tracker.tot_laps_n += 1
        self.tracker.tot_laps.setText(f"Total Laps: {self.tracker.tot_laps_n%2}")


    def handle_input(self, pos):
        if (( self.zoneA_span[0,0] <= pos[0]) and (pos[0] <= self.zoneA_span[0,1]) 
            and (self.zoneA_span[1,0] <= pos[1]) and (pos[1] <= self.zoneA_span[1,1])):
            self.zoneA()
        elif (( self.zoneB_span[0,0] <= pos[0]) and (pos[0] <= self.zoneB_span[0,1]) 
              and (self.zoneB_span[1,0] <= pos[1]) and (pos[1] <= self.zoneB_span[1,1])):
            self.zoneB()

class linear_tracker(QMainWindow):
    def __init__(self):
        super(linear_tracker, self).__init__()
        self.layout = QVBoxLayout()

        self.tot_laps = QLabel(f"Total Laps: 0")
        self.tot_laps_n = 0   

        self.exp_time = QLabel(f"Experiment Time: 0.00 s")
        self.current_trial_time = QLabel(f"Current Trial Time: 0.00 s")

        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        
        self.layout.addWidget(self.tot_laps)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.current_trial_time)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")
        self.current_trial_time.setText(f"Current Trial Time: {(datetime.now() - self.current_trial_start).total_seconds():.2f} s")

        

