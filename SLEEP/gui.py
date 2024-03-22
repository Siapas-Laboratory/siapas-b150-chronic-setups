from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi import *
from pyBehavior.interfaces.ni import *
from pyBehavior.interfaces.socket import Position
from pyBehavior.interfaces.socket import EventstringSender

class SLEEP(SetupGUI):
    def __init__(self):
        super(SLEEP, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()

    def buildUI(self):

        self.ev_logger = EventstringSender()
        self.layout.addWidget(self.ev_logger)

        self.pump1 = PumpConfig(self.client, 'pump1', ['module6'])
        self.layout.addWidget(self.pump1)

        self.mod = RPIRewardControl(self.client, 'module6')
        self.reward_modules.update({'a': self.mod})

        #format widgets
        self.layout.addWidget(self.mod)

        # start digital input threads
        # threads to monitor licking
        self.lick_thread = RPILickThread(self.client, "module1")
        self.lick_thread.lick_num_updated.connect(self.register_lick)
        self.lick_thread.start()


    def register_lick(self, amt):
        if self.running:
            self.state_machine.handle_input({"type": "lick", "amt":amt})
        self.log(f"{amt} licks", trigger_event=False)
    
    def log(self, msg, trigger_event = True):
        if trigger_event:
            digital_write(self.mapping.loc['event0'], True)
        self.ev_logger.send(msg)
        super(SLEEP, self).log(msg)
        if trigger_event:
            digital_write(self.mapping.loc['event0'], False)