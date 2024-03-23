from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi.remote import *
from pyBehavior.interfaces.ni import *
import nidaqmx
from pyBehavior.interfaces.socket import Position


class OPENFIELD_LINEAR(SetupGUI):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.sock = None
        self.buildUI()

    def buildUI(self):

        try:
            self.event_line = 'event0'
            ev_logger = self.add_eventstring_handler(self.event_line, self.mapping.loc[self.event_line])
            self.layout.addWidget(ev_logger)
        except nidaqmx.errors.DaqNotSupportedError:
            self.logger.warning("nidaqmx not supported on this device. could not start eventstring handler")
            self.event_line = None

        self.position = Position()
        self.register_state_machine_input(self.position.new_position,
                                          "pos", before = lambda x: self.pos.setText(str(x)),
                                          event_line = self.event_line)
        self.position.start()
        self.layout.addWidget(self.position)

        self.pump1 = PumpConfig(self.client, 'pump1', ['module1', 'module2'])
        self.layout.addWidget(self.pump1)

        self.mod1 = RPIRewardControl(self.client, 'module1')
        self.register_state_machine_input(self.mod1.new_licks,
                                          "lick", metadata = {"arm": "a"},
                                          before = lambda x: self.log(f" a {x} licks"),
                                          event_line = self.event_line)
        self.mod2 = RPIRewardControl(self.client, 'module2')
        self.register_state_machine_input(self.mod2.new_licks,
                                          "lick", metadata = {"arm": "b"},
                                          before = lambda x: self.log(f" b {x} licks"),
                                          event_line = self.event_line)

        self.reward_modules.update({'a': self.mod1, 
                                    'b': self.mod2})

        #format widgets
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(self.mod1)
        mod_layout.addWidget(self.mod2)
        self.layout.addLayout(mod_layout)