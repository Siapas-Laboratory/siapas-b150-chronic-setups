from statemachine import State
from PyQt5.QtCore import  QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QGroupBox, QCheckBox, QButtonGroup, QRadioButton
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
    stem_small_reward = State("stem_small_reward")

    a_reward= State("a_reward")
    a_no_reward = State("a_no_reward")
    a_small_reward = State("a_small_reward")
    a_baited = State("a_baited")

    b_reward= State("b_reward")
    b_no_reward = State("b_no_reward")
    b_small_reward = State("b_small_reward")
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
               | a_no_reward.to(b_small_reward, on = "deliver_small_reward", after = "log_correct")
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
                                'beam22': self.beamS2})
        self.tracker = tracker(self)
        self.tracker.show()
        self.cue_stem()
        self.thread_pool = ThreadPool(processes=5)
        self.target = None
        self.prev_target = None
        self.is_probe = True

    def a_next(self):
        mode = self.tracker.mode.checkedButton().text()
        if mode == 'Force A Cued':
            self.target = 'a'
            self.is_probe = False
        elif mode == 'Force B Cued':
            self.target = 'b'
            self.is_probe = False
        elif mode == 'Force Probe':
            self.target = 'b' if self.prev_target =='a' else 'a'
            self.is_probe = True
        return self.target == 'a'
    
    def clear_leds(self):
        for i in self.parent.reward_modules:
            self.turn_off_led(i)

    def cue_arm(self, arm, timeout = None):
        mod = self.parent.reward_modules[arm]
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on" , channel = 'run'))
        if not led_state:
            mod.toggle_led()
            if timeout is not None:
                self.thread_pool.apply(self.turn_off_led, (arm, timeout))

    def turn_off_led(self, arm, delay=None):
        if delay is not None:
            time.sleep(delay)
        mod = self.parent.reward_modules[arm]
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on" , channel = 'run'))
        if led_state:
            mod.toggle_led()
    
    def cue_stem(self):
        self.clear_leds()
        self.cue_arm('s')
    
    def cue_target(self):
        cue = True
        timeout=None
        self.clear_leds()
        self.tracker.is_probe.setChecked(self.is_probe)
        if self.is_probe:
            self.parent.log("probe trial")
            cue = self.tracker.blink_probe_cue.isChecked()
            if cue:
                self.parent.log("blinking cue")
                timeout = float(self.tracker.probe_cue_blink_time.text())
        self.tracker.increment_trial_type(self.target, self.is_probe)
        if cue: self.cue_arm(self.target, timeout=timeout)
        self.tracker.current_trial_start = datetime.now()
        self.prev_target = self.target
        
    def log_correct(self):
        arm = self.current_state.id[0]
        if 'small' in self.current_state.id:
            self.parent.log(f"arm {arm} correct but initially incorrect")
        else:
            self.parent.log(f"arm {arm} correct")
            self.tracker.increment_correct(arm, self.is_probe)
            self.cue_stem()

    def log_incorrect(self):
        self.parent.log(f"arm {self.current_state.id[0]} incorrect")
        self.cue_stem()
    
    def toggle_target(self, source, target):
        if (source.id == 'wandering') or ('small' in source.id):
            self.parent.log(f"stem correct but initially incorrect")
        else:
            self.parent.log(f"stem correct")
            self.tracker.correct_inbound.val += 1
        if 'small' in target.id:
            self.deliver_small_reward(target)
        else:
            self.deliver_reward(target)
        self.tracker.trial_count.val += 1
        probe_prob =  float(self.tracker.probe_prob.text())
        self.is_probe = False if self.is_probe else np.random.uniform() < probe_prob
        if self.is_probe:
            self.target = 'b' if self.prev_target == 'a' else 'a'
        else:
            if self.tracker.sticky.isChecked():
                if self.target is None:
                    a_prob = float(self.tracker.a_prob.text())
                    p = [a_prob, 1-a_prob]
                elif self.target == 'a':
                    p_aa = float(self.tracker.p_aa.text())
                    p = [p_aa, 1-p_aa]
                else:
                    p_bb = float(self.tracker.p_bb.text())
                    p = [1-p_bb, p_bb]
            else:
                a_prob = float(self.tracker.a_prob.text())
                p = [a_prob, 1-a_prob]
            self.target = ['a','b'][np.random.choice(2, p = p)]

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
        
        probe_prob_layout = QHBoxLayout()
        probe_prob_layout.addWidget(QLabel("Probe Trial Probability [0-1]:"))
        self.probe_prob = LoggableLineEdit("probe_prob", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.probe_prob.setValidator(only_frac)
        self.probe_prob.setText('0.1')
        probe_prob_layout.addWidget(self.probe_prob)

        blink_probe_cue_layout = QHBoxLayout()
        blink_probe_cue_layout.addWidget(QLabel("Blink Probe Cue:"))
        self.blink_probe_cue = QCheckBox()
        self.blink_probe_cue.setChecked(False)
        self.blink_probe_cue.stateChanged.connect(self.log_blink_probe_cue)
        blink_probe_cue_layout.addWidget(self.blink_probe_cue)

        blink_time_layout = QHBoxLayout()
        blink_time_layout.addWidget(QLabel("Probe Trial Cue Blink Time [s]:"))
        self.probe_cue_blink_time = LoggableLineEdit("blink_time", self.parent.parent)
        self.probe_cue_blink_time.setText("5")
        self.probe_cue_blink_time.setValidator(QDoubleValidator())
        self.probe_cue_blink_time.setEnabled(False)
        blink_time_layout.addWidget(self.probe_cue_blink_time)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode = QButtonGroup()
        rand = QRadioButton("Auto")
        mode_layout.addWidget(rand)
        rand.setChecked(True)
        self.mode.addButton(rand, id=0)
        force_a = QRadioButton("Force A Cued")
        mode_layout.addWidget(force_a)
        self.mode.addButton(force_a, id=1)
        force_b = QRadioButton("Force B Cued")
        mode_layout.addWidget(force_b)
        self.mode.addButton(force_b, id=2)
        force_probe = QRadioButton("Force Probe")
        mode_layout.addWidget(force_probe)
        self.mode.addButton(force_probe, id=3)

        sticky_layout = QHBoxLayout()
        sticky_layout.addWidget(QLabel("Specify Transition Probabilities:"))
        self.sticky = QCheckBox()
        self.sticky.setChecked(True)
        self.sticky.stateChanged.connect(self.log_sticky)
        sticky_layout.addWidget(self.sticky)

        p_aa_layout = QHBoxLayout()
        p_aa_layout.addWidget(QLabel("P(A|A):"))
        self.p_aa = LoggableLineEdit("p_aa", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.p_aa.setText("0.5")
        self.p_aa.setValidator(only_frac)
        self.p_aa.editingFinished.connect(self.update_a_prob)
        p_aa_layout.addWidget(self.p_aa)

        p_bb_layout = QHBoxLayout()
        p_bb_layout.addWidget(QLabel("P(B|B):"))
        self.p_bb = LoggableLineEdit("p_bb", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.p_bb.setText("0.5")
        self.p_bb.setValidator(only_frac)
        self.p_bb.editingFinished.connect(self.update_a_prob)
        p_bb_layout.addWidget(self.p_bb)

        a_prob_layout = QHBoxLayout()
        a_prob_layout.addWidget(QLabel("A Cued Probability [0-1]:"))
        self.a_prob = LoggableLineEdit("a_prob", self.parent.parent)
        only_frac = QDoubleValidator(0., 1., 6, notation = QDoubleValidator.StandardNotation)
        self.a_prob.setValidator(only_frac)
        self.update_a_prob()
        self.a_prob.setEnabled(False)
        a_prob_layout.addWidget(self.a_prob)

        probs = QGroupBox()
        playout = QVBoxLayout()
        playout.addLayout(sticky_layout)
        playout.addLayout(p_aa_layout)
        playout.addLayout(p_bb_layout)
        playout.addLayout(a_prob_layout)
        probs.setLayout(playout)

        settings = QGroupBox()
        slayout = QVBoxLayout()
        slayout.addLayout(reward_amount_layout)
        slayout.addLayout(small_rew_layout)
        slayout.addLayout(stem_small_rew_layout)
        slayout.addLayout(probe_prob_layout)
        slayout.addLayout(blink_probe_cue_layout)
        slayout.addLayout(blink_time_layout)
        slayout.addLayout(a_prob_layout)
        slayout.addLayout(mode_layout)
        slayout.addWidget(probs)
        settings.setLayout(slayout)
        self.layout.addWidget(settings)

        is_probe_layout = QHBoxLayout()
        is_probe_layout.addWidget(QLabel("Probe Trial:"))
        self.is_probe = QCheckBox()
        self.is_probe.setChecked(False)
        self.is_probe.setEnabled(False)
        is_probe_layout.addWidget(self.is_probe)

        self.tot_rewards = Parameter("Total # Rewards", default = 0, is_num = True)
        self.total_reward = Parameter("Total Reward [mL]", default =  0, is_num = True)
        self.trial_count = Parameter("Trial Count", default=0, is_num=True)
        self.correct_outbound = Parameter("# correct outbound", default=0, is_num=True)
        self.correct_inbound = Parameter("# correct inbound", default=0, is_num=True)
        self.current_state = Parameter("current state", default="*waiting to start*")
        self.exp_time = Parameter(f"Experiment Time [min]", default = 0, is_num=True)
        self.current_trial_time = Parameter(f"Current Trial Time [s]", default = 0, is_num=True)
        self.t_start = datetime.now()
        self.current_trial_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)

        a = QGroupBox()
        alayout = QVBoxLayout()
        a.setTitle("Arm A")
        self.correct_a_probes = Parameter("# correct a probes", default=0, is_num=True)
        self.a_probes = Parameter("# a probes", default=0, is_num=True)
        self.correct_a_cued = Parameter("# correct a cued", default=0, is_num=True)
        self.a_cued = Parameter("# a cued", default=0, is_num=True)
        alayout.addWidget(self.correct_a_probes)
        alayout.addWidget(self.a_probes)
        alayout.addWidget(self.correct_a_cued)
        alayout.addWidget(self.a_cued)
        a.setLayout(alayout)

        b = QGroupBox()
        blayout = QVBoxLayout()
        b.setTitle("Arm B")
        self.correct_b_probes = Parameter("# correct b probes", default=0, is_num=True)
        self.b_probes = Parameter("# b probes", default=0, is_num=True)
        self.correct_b_cued = Parameter("# correct b cued", default=0, is_num=True)
        self.b_cued = Parameter("# b cued", default=0, is_num=True)
        blayout.addWidget(self.correct_b_probes)
        blayout.addWidget(self.b_probes)
        blayout.addWidget(self.correct_b_cued)
        blayout.addWidget(self.b_cued)
        b.setLayout(blayout)

        info = QGroupBox()
        ilayout = QVBoxLayout()
        ilayout.addLayout(is_probe_layout)
        ilayout.addWidget(a)
        ilayout.addWidget(b)
        ilayout.addWidget(self.trial_count)
        ilayout.addWidget(self.correct_outbound)
        ilayout.addWidget(self.correct_inbound)
        ilayout.addWidget(self.current_state)
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
    
    def log_blink_probe_cue(self, i):
        self.parent.parent.log(f"blink_probe_cue set to {self.blink_probe_cue.isChecked()}")
        self.probe_cue_blink_time.setEnabled(self.blink_probe_cue.isChecked())


    def log_sticky(self):
        sticky = self.sticky.isChecked()
        self.parent.parent.log(f"sticky set to {sticky}")
        self.p_aa.setEnabled(sticky)
        self.p_bb.setEnabled(sticky)
        self.a_prob.setEnabled(not sticky)
        if sticky: self.update_a_prob()

    def update_a_prob(self):
        p_aa = float(self.p_aa.text())
        p_bb = float(self.p_bb.text())
        p_ab = 1 - p_bb
        p = p_ab/(1 - p_aa + p_ab)
        self.a_prob.setText(f"{p}")

    def update_time(self):
        self.exp_time.setText(f"{(datetime.now() - self.t_start).total_seconds()/60:.2f}")
        self.current_trial_time.setText(f"{(datetime.now() - self.current_trial_start).total_seconds():.2f}")

    def increment_reward(self, amount = None):
        if amount is None:
            amount = float(self.reward_amount.text())
        self.tot_rewards.val += 1
        self.total_reward.val += amount
    
    def increment_trial_type(self, target, probe):
        if probe:
            if target == 'a':
                self.a_probes.val += 1
            else:
                self.b_probes.val += 1
        else:
            if target == 'a':
                self.a_cued.val += 1
            else:
                self.b_cued.val += 1

    def increment_correct(self, target, probe):
        self.correct_outbound.val += 1
        if probe:
            if target == 'a':
                self.correct_a_probes.val += 1
            else:
                self.correct_b_probes.val += 1
        else:
            if target == 'a':
                self.correct_a_cued.val += 1
            else:
                self.correct_b_cued.val += 1
