from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QGroupBox, QCheckBox
from PyQt5.QtGui import  QDoubleValidator
from datetime import datetime
import pandas as pd
from pyBehavior.protocols import Protocol
from pyBehavior.gui import LoggableLineEdit, Parameter
import numpy as np
from multiprocessing.pool import ThreadPool
import time

class non_match_position(Protocol):

    sleep = State("sleep", initial=True)
    stem_reward= State("stem_reward")
    stem_small_reward = State("stem_smzall_reward")

    a_reward= State("a_reward", enter = "cue_stem")
    a_no_reward = State("a_no_reward", enter = "cue_stem")
    a_small_reward = State("a_small_reward", enter = "cue_stem")
    a_baited = State("a_baited")

    b_reward= State("b_reward", enter = "cue_stem")
    b_no_reward = State("b_no_reward", enter = "cue_stem")
    b_small_reward = State("b_small_reward", enter = "cue_stem")
    b_baited = State("b_baited")

    wandering = State("wandering")

    beamA =  ( a_baited.to(a_reward, on = "deliver_reward", after = "log_correct") 
               | b_baited.to(a_no_reward, after = "log_incorrect") 
               | b_no_reward.to(a_small_reward, on = "deliver_small_reward", after = "log_correct")
               | b_reward.to(wandering) |  b_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself()
               | a_reward.to.itself() 
               | a_no_reward.to.itself() 
               | a_small_reward.to.itself()
    )

    beamB =  ( b_baited.to(b_reward, on = "deliver_reward", after = "log_correct") 
               | a_baited.to(b_no_reward, after = "log_incorrect") 
               | a_no_reward.to(b_small_reward, on = "deliver_small_reward",after = "log_correct")
               | a_reward.to(wandering) | a_small_reward.to(wandering)
               | sleep.to(wandering) | wandering.to.itself() 
               | b_reward.to.itself() 
               | b_no_reward.to.itself() 
               | b_small_reward.to.itself()
    )

    beamS =  ( a_reward.to(stem_reward,  after =  "toggle_target") 
               | a_no_reward.to(stem_reward,  after =  "toggle_target") 
               | a_small_reward.to(stem_small_reward,  after = "toggle_target")
               | b_reward.to(stem_reward,  after = "toggle_target") 
               | b_no_reward.to(stem_reward,  after =  "toggle_target") 
               | b_small_reward.to(stem_small_reward,  after =  "toggle_target") 
               | wandering.to(stem_small_reward,  after =  "toggle_target") 
               | sleep.to(stem_reward,  after =  "toggle_target")
               | stem_reward.to.itself() 
               | stem_small_reward.to.itself()
               | a_baited.to.itself()
               | b_baited.to.itself()
    )

    beamS2 = ( stem_reward.to(a_baited, cond = 'a_next', after = 'cue_target')
               | stem_reward.to(b_baited, after = 'cue_target')
               | stem_small_reward.to(a_baited, cond = 'a_next', after = 'cue_target')
               | stem_small_reward.to(b_baited, after = 'cue_target')
               | a_baited.to.itself() | b_baited.to.itself()
               | a_reward.to.itself() | a_no_reward.to.itself() | a_small_reward.to.itself()
               | b_reward.to.itself() | b_no_reward.to.itself() | b_small_reward.to.itself()
               | wandering.to.itself() | sleep.to.itself()
    )


    def __init__(self, parent):
        super(non_match_position, self).__init__(parent)
        self.init = False
        self.beams = pd.Series({'beam8': self.beamB, 
                                'beam16': self.beamA, 
                                'beam17': self.beamS,
                                'beam18': self.beamS2})
        self.tracker = tracker(self)
        self.tracker.show()
        self.cue_stem()
        self.thread_pool = ThreadPool(processes=5)

    
    @property
    def is_probe(self):
        return (self.tracker.trial_count.val %2) == 0

    def a_next(self):
        return self.target == 'a'
    
    def clear_leds(self):
        for i in self.parent.reward_modules:
            self.turn_off_led(i)

    def cue_arm(self, arm, timeout = None):
        mod = self.parent.reward_modules[arm]
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on"))
        if not led_state:
            mod.toggle_led()
            if timeout is not None:
                self.thread_pool.apply(self.turn_off_led, (arm, timeout))

    def turn_off_led(self, arm, delay=None):
        if delay is not None:
            time.sleep(delay)
        mod = self.parent.reward_modules[arm]
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on"))
        if led_state:
            mod.toggle_led()
    
    def cue_stem(self):
        self.clear_leds()
        self.cue_arm('s')
    
    def cue_target(self):
        cue = True
        timeout=None
        self.clear_leds()
        if self.is_probe:
            cue = self.tracker.cue_probe.isChecked()
            if self.tracker.blink_probe_cue.isChecked():
                timeout = float(self.tracker.probe_cue_blink_time.text())
        if cue: self.cue_arm(self.target, timeout=timeout)
        self.tracker.current_trial_start = datetime.now()
        
    def log_correct(self):
        if 'small' in self.current_state.id:
            self.parent.log(f"arm {self.current_state.id[0]} correct but initially incorrect")
        else:
            self.parent.log(f"arm {self.current_state.id[0]} correct")
            self.tracker.correct_outbound.val += 1
            if self.is_probe:
                if self.target == 'a':
                    self.tracker.correct_a_probes.val += 1
                else:
                    self.tracker.correct_b_probes.val += 1

    def log_incorrect(self):
        self.parent.log(f"arm {self.current_state.id[0]} incorrect")
    
    def toggle_target(self):
        if "small" in self.current_state.id:
            self.parent.log(f"stem correct but initially incorrect")
            self.deliver_small_reward(self.current_state)
        else:
            self.parent.log(f"stem correct")
            self.tracker.correct_inbound.val += 1
            self.deliver_reward(self.current_state)
        self.tracker.trial_count.val += 1
        if self.is_probe:
            self.target = 'b' if self.target=='a' else 'a'
        else:
            self.target = ['a','b'][np.random.choice(2)]
        self.tracker.target.setText(f"{self.target}")

    def deliver_reward(self, target):
        arm = target.id[0]
        self.parent.trigger_reward(arm, float(self.tracker.reward_amount.text()), force = False, enqueue = True)
        self.tracker.increment_reward()

    def deliver_small_reward(self, target):
        arm = target.id[0]
        if arm == 's':
            frac = float(self.tracker.stem_small_rew_frac.text())
        else:
            frac = float(self.tracker.small_rew_frac.text())
        amt = float(self.tracker.reward_amount.text()) * frac
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
        self.reward_amount.setText("0.1")
        self.reward_amount.setValidator(QDoubleValidator())
        reward_amount_layout.addWidget(reward_amount_label)
        reward_amount_layout.addWidget(self.reward_amount)

        small_rew_layout = QHBoxLayout()
        small_rew_label = QLabel("Small Reward Fraction: ")
        self.small_rew_frac = LoggableLineEdit("small_reward_frac", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.small_rew_frac.setText("0.0")
        self.small_rew_frac.setValidator(only_frac)
        small_rew_layout.addWidget(small_rew_label)
        small_rew_layout.addWidget(self.small_rew_frac)

        stem_small_rew_layout = QHBoxLayout()
        stem_small_rew_label = QLabel("Stem Small Reward Fraction: ")
        self.stem_small_rew_frac = LoggableLineEdit("stem_small_reward_frac", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.stem_small_rew_frac.setText("1.0")
        self.stem_small_rew_frac.setValidator(only_frac)
        stem_small_rew_layout.addWidget(stem_small_rew_label)
        stem_small_rew_layout.addWidget(self.stem_small_rew_frac)

        cue_probe_layout = QHBoxLayout()
        cue_probe_layout.addWidget(QLabel("Cue Probe Trials:"))
        self.cue_probe = QCheckBox()
        self.cue_probe.setChecked(True)
        self.cue_probe.stateChanged.connect(self.log_cue_probe)
        cue_probe_layout.addWidget(self.cue_probe)

        blink_probe_cue_layout = QHBoxLayout()
        blink_probe_cue_layout.addWidget(QLabel("Blink Probe Cue:"))
        self.blink_probe_cue = QCheckBox()
        self.blink_probe_cue.setChecked(False)
        self.blink_probe_cue.stateChanged.connect(self.log_cue_probe)
        blink_probe_cue_layout.addWidget(self.blink_probe_cue)

        blink_time_layout = QHBoxLayout()
        blink_time_layout.addWidget(QLabel("Probe Trial Cue Blink Time [s]:"))
        self.probe_cue_blink_time = LoggableLineEdit("c", self.parent.parent)
        self.probe_cue_blink_time.setText("5")
        self.probe_cue_blink_time.setValidator(QDoubleValidator())
        self.probe_cue_blink_time.setEnabled(False)
        blink_time_layout.addWidget(self.probe_cue_blink_time)

        settings = QGroupBox()
        slayout = QVBoxLayout()
        slayout.addLayout(reward_amount_layout)
        slayout.addLayout(small_rew_layout)
        slayout.addLayout(stem_small_rew_layout)
        slayout.addLayout(cue_probe_layout)
        slayout.addLayout(blink_probe_cue_layout)
        slayout.addLayout(blink_time_layout)
        settings.setLayout(slayout)
        self.layout.addWidget(settings)

        self.tot_rewards = Parameter("Total # Rewards", default = 0, is_num = True)
        self.total_reward = Parameter("Total Reward [mL]", default =  0, is_num = True)
        self.trial_count = Parameter("Trial Count", default=0, is_num=True)
        self.correct_outbound = Parameter("# correct outbound", default=0, is_num=True)
        self.correct_a_probes = Parameter("# correct a probes", default=0, is_num=True)
        self.correct_b_probes = Parameter("# correct b probes", default=0, is_num=True)
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
        ilayout.addWidget(self.correct_a_probes)
        ilayout.addWidget(self.correct_b_probes)
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
        self.blink_probe_cue.setEnabled(self.cue_probe.isChecked())
        self.probe_cue_blink_time.setEnabled(self.cue_probe.isChecked() and self.blink_probe_cue.isChecked())

    def log_blink_probe_cue(self, i):
        self.parent.parent.log(f"blink_probe_cue set to {self.blink_probe_cue.isChecked()}")
        self.probe_cue_blink_time.setEnabled(self.cue_probe.isChecked() and self.blink_probe_cue.isChecked())

    def update_time(self):
        self.exp_time.setText(f"{(datetime.now() - self.t_start).total_seconds()/60:.2f}")
        self.current_trial_time.setText(f"{(datetime.now() - self.current_trial_start).total_seconds():.2f}")

    def increment_reward(self, amount = None):
        if not amount:
            amount = float(self.reward_amount.text())
        self.tot_rewards.val += 1
        self.total_reward.val += amount