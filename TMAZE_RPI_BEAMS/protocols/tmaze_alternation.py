from statemachine import StateMachine, State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
import pandas as pd
from pyBehavior.protocols import Protocol


class tmaze_alternation(Protocol):

    sleep = State("sleep", initial=True)
    stem_reward= State("stem_reward")
    stem_small_reward = State("stem_small_reward")

    a_reward= State("a_reward")
    a_no_reward = State("a_no_reward")
    a_small_reward = State("a_small_reward")

    b_reward= State("b_reward")
    b_no_reward = State("b_no_reward")
    b_small_reward = State("b_small_reward")

    wandering = State("wandering")

    beamA =  ( stem_reward.to(a_reward, cond="correct_arm",  after = "deliver_reward") 
               | stem_reward.to(a_no_reward, cond="incorrect_arm") 
               | stem_small_reward.to(a_reward, cond="correct_arm",  after = "deliver_reward") 
               | stem_small_reward.to(a_no_reward, cond="incorrect_arm") 
               | b_no_reward.to(a_small_reward, cond = "correct_arm",  after = "deliver_small_reward")
               | b_reward.to(wandering) |  b_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself()
               | a_reward.to.itself() 
               | a_no_reward.to.itself() 
               | a_small_reward.to.itself()
    )


    beamB =  ( stem_reward.to(b_reward, cond="correct_arm", after = "deliver_reward") 
               | stem_reward.to(b_no_reward, cond="incorrect_arm") 
               | stem_small_reward.to(b_reward, cond="correct_arm",  after = "deliver_reward") 
               | stem_small_reward.to(b_no_reward, cond="incorrect_arm") 
               | a_no_reward.to(b_small_reward, cond = "correct_arm",  after = "deliver_small_reward")
               | a_reward.to(wandering) | a_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself() 
               | b_reward.to.itself() 
               | b_no_reward.to.itself() 
               | b_small_reward.to.itself()
    )

    beamS =  ( a_reward.to(stem_reward,  after =  "toggle_target") 
               | a_no_reward.to(stem_small_reward,  after =  "toggle_target") 
               | a_small_reward.to(stem_small_reward,  after = "toggle_target")
               | b_reward.to(stem_reward,  after = "toggle_target") 
               | b_no_reward.to(stem_small_reward,  after =  "toggle_target") 
               | b_small_reward.to(stem_small_reward,  after =  "toggle_target") 
               | wandering.to(stem_small_reward,  after =  "toggle_target") 
               | sleep.to(stem_reward,  after =  "toggle_target")
               | stem_reward.to.itself() 
               | stem_small_reward.to.itself()
    )


    def __init__(self, parent):
        super(tmaze_alternation, self).__init__(parent)
        self.target = None
        self.init = False
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA, 
                                'beam17': self.beamS })
        self.tracker = tmaze_tracker()
        self.tracker.show()


    def correct_arm(self, event_data):
        if self.target is None:
            self.target = event_data.target.id[0]
        correct = self.target == event_data.target.id[0]
        if correct:
            if "small" in event_data.target.id:
                self.parent.log(f"arm {event_data.target.id[0]} correct but initially incorrect")
            else:
                self.parent.log(f"arm {event_data.target.id[0]} correct")
                self.tracker.correct_outbound += 1
                self.tracker.correct_outbound_label.setText(f"# correct outbound: {self.tracker.correct_outbound}")
                self.tracker.trial_count += 1
                self.tracker.trial_count_label.setText(f"Trial Count: {self.tracker.trial_count}")
        return correct

    def incorrect_arm(self, event_data):
        if self.target is None:
            return False
        else:
            incorrect = self.target != event_data.target.id[0]
            if incorrect:
                self.parent.log(f"arm {event_data.target.id[0]} incorrect")
                self.tracker.trial_count += 1
                self.tracker.trial_count_label.setText(f"Trial Count: {self.tracker.trial_count}")
            return incorrect
    
    def toggle_target(self, event_data):
        if "small" in event_data.target.id:
            self.parent.log(f"stem correct but initially incorrect")
            self.deliver_small_reward()
        else:
            self.parent.log(f"stem correct")
            self.tracker.correct_inbound += 1
            self.tracker.correct_inbound_label.setText(f"# correct inbound: {self.tracker.correct_inbound}")
            self.deliver_reward()
        if not self.init:
            self.init = True
            return
        else:
            self.target = 'b' if self.target=='a' else 'a'
            self.tracker.target.setText(f"target: {self.target}")
        self.tracker.current_trial_start = datetime.now()

    def deliver_reward(self):
        self.parent.trial_lick_n = 0
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, False)


    def deliver_small_reward(self):
        self.parent.trial_lick_n = 0
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, True)

    def handle_input(self, dg_input):
        if dg_input['type'] == "beam":
            if dg_input in self.beams.index:
                self.beams[dg_input]()
            self.tracker.current_state.setText(f"current state: {self.current_state.id}")

class tmaze_tracker(QMainWindow):
    def __init__(self):
        super(tmaze_tracker, self).__init__()
        self.layout = QVBoxLayout()
        self.trial_count = 0
        self.correct_outbound = 0
        self.correct_inbound = 0
        self.trial_count_label = QLabel(f"Trial Count: 0")
        self.correct_outbound_label = QLabel(f"# correct outbound: 0")
        self.correct_inbound_label = QLabel(f"# correct inbound: 0")
        self.current_state = QLabel("current state: *waiting to start*")
        self.target =  QLabel("target: no target")
        self.exp_time = QLabel(f"Experiment Time: 0.00 s")
        self.current_trial_time = QLabel(f"Current Trial Time: 0.00 s")
        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.layout.addWidget(self.trial_count_label)
        self.layout.addWidget(self.correct_outbound_label)
        self.layout.addWidget(self.correct_inbound_label)
        self.layout.addWidget(self.current_state)
        self.layout.addWidget(self.target)
        self.layout.addWidget(self.exp_time)
        self.layout.addWidget(self.current_trial_time)
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer.start(1000)

    def update_time(self):
        self.exp_time.setText(f"Experiment Time: {(datetime.now() - self.t_start).total_seconds():.2f} s")
        self.current_trial_time.setText(f"Current Trial Time: {(datetime.now() - self.current_trial_start).total_seconds():.2f} s")