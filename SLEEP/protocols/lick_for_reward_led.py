from pyBehavior.protocols import Protocol
from pyBehavior.gui import Parameter, LoggableLineEdit
from PyQt5.QtWidgets import QMainWindow,QHBoxLayout, QVBoxLayout, QWidget, QLabel, QLineEdit, QGroupBox
from PyQt5.QtGui import  QDoubleValidator
from PyQt5.QtCore import  QTimer
from datetime import datetime
from statemachine import State
import random

class lick_for_reward_led(Protocol):
    
    armed = State(initial=True)
    not_armed = State()
    licking = State()

    lick = (armed.to(licking, cond='sub_thresh')| 
            armed.to(not_armed, on ='reward', after = 'start_timeout') |
            licking.to.itself(cond='sub_thresh') |
            licking.to(not_armed, on = 'reward', after = 'start_timeout') |
            not_armed.to.itself())
    
    timeout = not_armed.to(armed, on='cue')

    def __init__(self, parent):
        super(lick_for_reward_led, self).__init__(parent)
        self.tracker = tracker(self)
        self.tracker.show()
    
    def sub_thresh(self):
        return self.tracker.curr_trial_licks.val < float(self.tracker.threshold.text())

    def cue(self):
        mod = self.parent.reward_modules['a']
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on"))
        if not led_state: mod.toggle_led()

    def reward(self):
        mod = self.parent.reward_modules['a']
        led_state = bool(self.parent.client.get(f"modules['{mod.module}'].LED.on"))
        if led_state: mod.toggle_led()
        self.parent.trigger_reward('a', float(self.tracker.reward_amount.text()), force = False, enqueue = True)
        self.tracker.increment_reward()

    def start_timeout(self):
        self.tracker.reset_timeout_timer()
        self.tracker.timeout.val = random.uniform(float(self.tracker.min_timeout.text()), 
                                                  float(self.tracker.max_timeout.text()))
        self.start_countdown(self.tracker.timeout.val)
    
    def handle_input(self, data):
        if data['type'] == 'lick':
            self.tracker.increment_licks()
            self.lick()

class tracker(QMainWindow):
    def __init__(self, parent):
        super(tracker, self).__init__()
        self.parent = parent

        reward_amount_layout = QHBoxLayout()
        reward_amount_label = QLabel("Reward Amount (mL): ")
        self.reward_amount = LoggableLineEdit("reward_amount", self.parent.parent)
        self.reward_amount.setText("0.2")
        self.reward_amount.setValidator(QDoubleValidator())
        reward_amount_layout.addWidget(reward_amount_label)
        reward_amount_layout.addWidget(self.reward_amount)


        thresh_layout = QHBoxLayout()
        thresh_label = QLabel("Lick threshold: ")
        self.threshold = LoggableLineEdit("threshold", self.parent.parent)
        self.threshold.setText(f"{5}")
        self.threshold.setValidator(QDoubleValidator())
        thresh_layout.addWidget(thresh_label)
        thresh_layout.addWidget(self.threshold)

        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("Timeout Range [s]:"))
        to_layout.addWidget(QLabel("Min:"))
        self.min_timeout = LoggableLineEdit('min_timeout', self.parent.parent)
        self.min_timeout.setText(f"{5}")
        self.min_timeout.setValidator(QDoubleValidator())
        to_layout.addWidget(self.min_timeout)
        to_layout.addWidget(QLabel("Max:"))
        self.max_timeout = LoggableLineEdit('max_timeout', self.parent.parent)
        self.max_timeout.setText(f"{300}")
        self.max_timeout.setValidator(QDoubleValidator())
        to_layout.addWidget(self.max_timeout)

        settings = QGroupBox()
        slayout = QVBoxLayout()
        slayout.addLayout(reward_amount_layout)
        slayout.addLayout(thresh_layout)
        slayout.addLayout(to_layout)
        settings.setLayout(slayout)
        settings.setTitle('Settings')

        self.tot_rewards = Parameter("Total # Rewards", default = 0, is_num = True)
        self.total_reward = Parameter("Total Reward [mL]", default = 0, is_num = True)
        self.exp_time = Parameter("Experiment Time [min]", default = 0, is_num = True)
        self.licks = Parameter("Lick Count", default = 0, is_num = True)
        self.curr_trial_licks = Parameter("Current Trial Lick Count", default = 0, is_num = True)
        self.next_trial_countdown = Parameter("Time Until Next Trial [s]", default = 0, is_num = True)
        self.timeout = Parameter("Timeout Period [s]", default = 5, is_num = True)
        
        info = QGroupBox()
        ilayout = QVBoxLayout()
        ilayout.addWidget(self.tot_rewards)
        ilayout.addWidget(self.total_reward)
        ilayout.addWidget(self.exp_time)
        ilayout.addWidget(self.licks)
        ilayout.addWidget(self.curr_trial_licks)
        info.setLayout(ilayout)
        info.setTitle('Info')

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(settings)
        layout.addWidget(info)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.t_start = datetime.now()
        self.to_start = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def reset_timeout_timer(self):
        self.to_start = datetime.now()

    def update_time(self):
        self.exp_time.val = (datetime.now() - self.t_start).total_seconds()/60.
        if self.parent.current_state.id == 'not_armed':
            self.next_trial_countdown.val = self.timeout.val - (datetime.now() - self.to_start).total_seconds()

    def increment_reward(self):
        self.tot_rewards.val += 1
        self.total_reward.val += float(self.reward_amount.text())
        self.reset_trial_licks()
    
    def reset_trial_licks(self):
        self.curr_trial_licks.val = 0

    def increment_licks(self):
        self.licks.val += 1
        if self.parent.current_state.id != 'not_armed': 
            self.curr_trial_licks.val += 1