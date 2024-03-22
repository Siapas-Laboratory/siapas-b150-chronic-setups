from statemachine import StateMachine, State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
import pandas as pd
from pyBehavior.protocols import Protocol


class tmaze_semi_guided(Protocol):

    sleep = State("sleep", initial=True)
    stem_reward= State("stem_reward")
    stem_small_reward = State("stem_small_reward")

    a_reward= State("a_reward")
    a_no_reward = State("a_no_reward")

    b_reward= State("b_reward")
    b_no_reward = State("b_no_reward")

    beamA =  ( stem_reward.to(a_reward, cond="correct_arm",  after = "deliver_reward") 
               | stem_reward.to(a_no_reward, cond="incorrect_arm", after = "raise_wall") 
               | stem_small_reward.to(a_reward, cond="correct_arm",  after = "deliver_reward") 
               | stem_small_reward.to(a_no_reward, cond="incorrect_arm", after = "raise_wall") 
               | b_no_reward.to(a_no_reward, after = "raise_wall")
               | b_reward.to(a_no_reward, after = "raise_wall")
               | a_reward.to.itself() 
               | a_no_reward.to.itself()
               | sleep.to.itself()
    )


    beamB =  ( stem_reward.to(b_reward, cond="correct_arm", after = "deliver_reward") 
               | stem_reward.to(b_no_reward, cond="incorrect_arm", after = "raise_wall") 
               | stem_small_reward.to(b_reward, cond="correct_arm", after = "deliver_reward") 
               | stem_small_reward.to(b_no_reward, cond="incorrect_arm", after = "raise_wall")
               | a_no_reward.to(b_no_reward, after = "raise_wall")
               | a_reward.to(b_no_reward, after = "raise_wall")
               | b_reward.to.itself() 
               | b_no_reward.to.itself() 
               | sleep.to.itself()
    )

    beamS =  ( a_reward.to(stem_reward,  before = "lower_walls", after =  "toggle_target") 
               | b_reward.to(stem_reward, before = "lower_walls", after = "toggle_target") 
               | a_no_reward.to(stem_small_reward, before = "lower_walls", after = "toggle_target")
               | b_no_reward.to(stem_small_reward, before = "lower_walls", after = "toggle_target")
               | sleep.to(stem_reward,  before = "lower_walls", after =  "toggle_target")
               | stem_reward.to.itself()
               | stem_small_reward.to.itself()
    )


    def __init__(self, parent):
        super(tmaze_semi_guided, self).__init__(parent)
        self.target = None
        self.init = False
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA, 
                                'beam17': self.beamS })
        for i in range(1,8):
            self.parent.doors.loc[f'door{i}', 'button'].setChecked(False)

        self.tracker = tmaze_tracker()
        self.tracker.show()

    def block_b(self):
        self.parent.doors.loc['door7','button'].setChecked(True)

    def block_a(self):
        self.parent.doors.loc['door5','button'].setChecked(True)
    
    def lower_walls(self):
        for i in range(1,8):
            if i != 2:
                self.parent.doors.loc[f'door{i}', 'button'].setChecked(False)
            else:
                self.parent.doors.loc[f'door{i}', 'button'].setChecked(True)

    def raise_wall(self):
        self.lower_walls()
        arm = self.current_state.id[0]
        if arm == 'a':
            self.block_b()
        elif arm =='b':
            self.block_a()


    def correct_arm(self, event_data):
        if self.target is None:
            self.target = event_data.target.id[0]
        correct = self.target == event_data.target.id[0]
        if correct:
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
            dest = event_data.target.id[0]
            incorrect = self.target != dest
            if incorrect:
                self.parent.log(f"arm {dest} incorrect")
                self.tracker.trial_count += 1
                self.tracker.trial_count_label.setText(f"Trial Count: {self.tracker.trial_count}")
            return incorrect
    
    def toggle_target(self):
        self.parent.log(f"stem correct")
        if 'small' in self.current_state.id:
            self.deliver_small_reward()
        else:
            self.deliver_reward()
        if not self.init:
            self.init = True
            return
        else:
            self.target = 'b' if self.target=='a' else 'a'
            self.tracker.target.setText(f"target: {self.target}")
        self.tracker.current_trial_start = datetime.now()

    def deliver_reward(self):
        self.raise_wall()
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, False)

    def deliver_small_reward(self):
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, True)


    def handle_input(self, sm_input):
        if sm_input["type"] == "beam":
            beam = sm_input["data"]
            if beam in self.beams.index:
                self.beams[beam]()
            self.tracker.current_state.setText(f"current state: {self.current_state.id}")

class tmaze_tracker(QMainWindow):
    def __init__(self):
        super(tmaze_tracker, self).__init__()
        self.layout = QVBoxLayout()
        self.trial_count = 0
        self.correct_outbound = 0
        self.trial_count_label = QLabel(f"Trial Count: 0")
        self.correct_outbound_label = QLabel(f"# correct outbound: 0")
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