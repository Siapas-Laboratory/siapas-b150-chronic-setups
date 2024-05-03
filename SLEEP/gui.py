from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi.remote import *
from pyBehavior.interfaces.ni import *
from pyBehavior.interfaces.socket import Position
import nidaqmx

class SLEEP(SetupGUI):
    def __init__(self):
        super(SLEEP, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()

    def buildUI(self):

        try:
            self.event_line = 'event0'
            ev_logger = self.add_eventstring_handler(self.event_line, self.mapping.loc[self.event_line])
            self.layout.addWidget(ev_logger)
        except nidaqmx.errors.DaqNotSupportedError:
            self.logger.warning("nidaqmx not supported on this device. could not start eventstring handler")
            self.event_line = None

        self.pump1 = PumpConfig(self.client, 'pump1', self,  ['module6'])
        self.layout.addWidget(self.pump1)

        self.mod = RPIRewardControl(self.client, 'module6', self)
        self.reward_modules.update({'a': self.mod})

        #format widgets
        self.layout.addWidget(self.mod)

        # start digital input threads
        # threads to monitor licking
        self.register_state_machine_input(self.mod.new_licks,
                                          "lick", before = lambda x: self.log(f"{x} licks", raise_event_line=False),
                                          event_line = self.event_line)