from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QGroupBox, QCheckBox
from PyQt5.QtGui import  QDoubleValidator
from datetime import datetime
import pandas as pd
from pyBehavior.protocols import Protocol
from pyBehavior.gui import LoggableLineEdit, Parameter
import numpy as np

class non_match_position(Protocol):

    sleep = State("sleep", initial=True, exit = "clear_leds")
    stem_reward= State("stem_reward")
    stem_small_reward = State("stem_smzall_reward")

    a_reward= State("a_reward", enter = "cue_stem")
    a_no_reward = State("a_no_reward", enter = "cue_stem")
    a_small_reward = State("a_small_reward", enter = "cue_stem")

    b_reward= State("b_reward", enter = "cue_stem")
    b_no_reward = State("b_no_reward", enter = "cue_stem")
    b_small_reward = State("b_small_reward", enter = "cue_stem")

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
        super(non_match_position, self).__init__(parent)
        self.target = None
        self.init = False
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA, 
                                'beam17': self.beamS })
        self.tracker = tracker(self)
        self.tracker.show()
        self.cue_stem()


    def correct_arm(self, event_data):
        if self.target is None:
            self.target = event_data.target.id[0]
        correct = self.target == event_data.target.id[0]
        if correct:
            if "small" in event_data.target.id:
                self.parent.log(f"arm {event_data.target.id[0]} correct but initially incorrect")
            else:
                self.parent.log(f"arm {event_data.target.id[0]} correct")
                self.tracker.correct_outbound.val += 1
        return correct
    
    def clear_leds(self):
        for i in self.parent.reward_modules:
            mod = self.parent.reward_modules[i].module
            led_state = bool(self.parent.client.get(f"modules['{mod}'].LED.on"))
            if led_state:
                self.parent.reward_modules[i].toggle_led()

    def cue_arm(self, arm):
        self.clear_leds()
        mod = self.parent.reward_modules[arm]
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on"))
        if not led_state:
            mod.toggle_led()
    
    def cue_stem(self):
        self.cue_arm('s')
        
    def incorrect_arm(self, event_data):
        if self.target is None:
            return False
        else:
            incorrect = self.target != event_data.target.id[0]
            if incorrect:
                self.parent.log(f"arm {event_data.target.id[0]} incorrect")
            return incorrect
    
    def toggle_target(self, event_data):
        if "small" in event_data.target.id:
            self.parent.log(f"stem correct but initially incorrect")
            self.deliver_small_reward()
        else:
            self.parent.log(f"stem correct")
            self.tracker.correct_inbound.val += 1
            self.deliver_reward()
        if not self.init:
            self.init = True
            return
        else:
            self.tracker.trial_count.val += 1
            is_probe = (self.tracker.trial_count.val %2) == 1
            cue = True
            if is_probe:
                self.target = 'b' if self.target=='a' else 'a'
                cue = self.tracker.cue_probe.isChecked()
            else:
                self.target = ['a','b'][np.random.choice(2)]
            self.tracker.target.setText(f"{self.target}")
            if cue: self.cue_arm(self.target)
        self.tracker.current_trial_start = datetime.now()

    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.trigger_reward(arm, self.tracker.reward_amount.val, force = False, enqueue = True)
        self.tracker.increment_reward()

    def deliver_small_reward(self):
        arm = self.current_state.id[0]
        amt = self.tracker.reward_amount.val * self.tracker.small_rew_frac.val
        self.parent.trigger_reward(arm, amt, force = False, enqueue = True)
        self.tracker.increment_reward(amt)

    def handle_input(self, sm_input):
        if sm_input['type'] == "beam":
            beam = sm_input['data']
            if beam in self.beams.index:
                self.beams[beam]()
            self.tracker.current_state.setText(f"{self.current_state.id}")


class tracker(QMainWindow):
    def __init__(self, parent):
        super(tracker, self).__init__()
        self.layout = QVBoxLayout()
        self.parent = parent
        reward_amount_layout = QHBoxLayout()
        reward_amount_label = QLabel("Reward Amount (mL): ")
        self.reward_amount = LoggableLineEdit("reward_amount", self.parent.parent)
        self.reward_amount.setText("0.2")
        self.reward_amount.setValidator(QDoubleValidator())
        reward_amount_layout.addWidget(reward_amount_label)
        reward_amount_layout.addWidget(self.reward_amount)

        small_rew_layout = QHBoxLayout()
        small_rew_label = QLabel("Small Reward Fraction: ")
        self.small_rew_frac = LoggableLineEdit("small_reward_frac", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.small_rew_frac.setText("0.6")
        self.small_rew_frac.setValidator(only_frac)
        small_rew_layout.addWidget(small_rew_label)
        small_rew_layout.addWidget(self.small_rew_frac)

        cue_probe_layout = QHBoxLayout()
        cue_probe_layout.addWidget(QLabel("Cue Probe Trials:"))
        self.cue_probe = QCheckBox()
        self.cue_probe.setChecked(True)
        self.cue_probe.stateChanged.connect(self.log_cue_probe)
        cue_probe_layout.addWidget(self.cue_probe)

        settings = QGroupBox()
        slayout = QVBoxLayout()
        slayout.addLayout(reward_amount_layout)
        slayout.addLayout(small_rew_layout)
        slayout.addLayout(cue_probe_layout)
        settings.setLayout(slayout)
        self.layout.addWidget(settings)


        self.tot_rewards = Parameter("Total # Rewards", default = 0, is_num = True)
        self.total_reward = Parameter("Total Reward [mL]", default =  0, is_num = True)
        self.trial_count = Parameter("Trial Count", default=0, is_num=True)
        self.correct_outbound = Parameter("# correct outbound", default=0, is_num=True)
        self.correct_inbound = Parameter("# correct inbound", default=0, is_num=True)
        self.current_state = Parameter("current state", default="*waiting to start*")
        self.target =  Parameter("target", default="no target")
        self.exp_time = Parameter(f"Experiment Time [min]", default = 0, is_num=True)
        self.current_trial_time = Parameter(f"Current Trial Time [s]", default = 0, is_num=True)
        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)

        info = QGroupBox()
        ilayout = QVBoxLayout()
        ilayout.addWidget(self.trial_count)
        ilayout.addWidget(self.correct_outbound)
        ilayout.addWidget(self.correct_inbound)
        ilayout.addWidget(self.current_state)
        ilayout.addWidget(self.target)
        ilayout.addWidget(self.tot_rewards)
        ilayout.addWidget(self.total_reward)
        ilayout.addWidget(self.exp_time)
        ilayout.addWidget(self.current_trial_time)
        info.setLayout(ilayout)
        self.layout.addWidget(info)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
        self.timer.start(1000)

    def log_cue_probe(self, i):
        self.parent.parent.log(f"cue_probe set to {self.cue_probe.isChecked()}")

    def update_time(self):
        self.exp_time.setText(f"{(datetime.now() - self.t_start).total_seconds()/60:.2f}")
        self.current_trial_time.setText(f"{(datetime.now() - self.current_trial_start).total_seconds():.2f}")

    def increment_reward(self, amount = None):
        if not amount:
            amount = float(self.reward_amount.text())
        self.tot_rewards.val += 1
        self.total_reward.val += amount