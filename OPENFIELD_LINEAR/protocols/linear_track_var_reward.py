from statemachine import State
from PyQt5.QtCore import  QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from datetime import datetime
import numpy as np
from pyBehavior.protocols import Protocol
import json

class Worker(QObject):

    finished = pyqtSignal(name = 'finished')

    def __init__(self, state_machine, gui):
        super(Worker, self).__init__()
        self.state_machine = state_machine
        self.gui = gui
        for i in self.gui.reward_modules:
            idx = self.gui.reward_modules[i].trigger_mode.findText("Single Trigger")
            self.gui.reward_modules[i].trigger_mode.setCurrentIndex(idx)

    def run(self):
        res = self.gui.client.run_command("trigger_reward_multiple",
                                            args = {
                                                "modules": ["module1", "module2"],
                                                "amount": float(self.gui.mod1.amt.text()),
                                                "trigger_mode": "SINGLE_TRIGGER",
                                                "trigger_name": "reset_lick_trigger",
                                            })
        res = json.loads(res)
        if res =='module1': 
            self.parent.log(f"arm a correct")
            self.state_machine.zoneB()
        elif res == 'module2': 
            self.parent.log(f"arm b correct")
            self.state_machine.zoneA()
        else:raise ValueError

        self.finished.emit()

class linear_track_var_reward(Protocol):

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
        super(linear_track_var_reward, self).__init__(parent)
        self.tracker = linear_tracker()
        self.tracker.show()

        self.task_thread = QThread()
        self.worker = Worker(self, self.parent)
        self.worker.moveToThread(self.task_thread)
        self.task_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.task_thread.quit)
        self.task_thread.start()

        
    def deliver_reward(self):
        arm = self.current_state.id[0]
        self.parent.log(f"arm {arm} baited")
        self.parent.trigger_reward(arm, False, force = False, wait = True)
        self.tracker.current_trial_start = datetime.now()
        self.tracker.tot_laps_n += 1
        self.tracker.tot_laps.setText(f"Total Laps: {self.tracker.tot_laps_n//2}")
        if self.parent.running:
            if arm == 'a': self.zoneB()
            else: self.zoneA()

    def handle_input(self, pos):
        pass

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

        

