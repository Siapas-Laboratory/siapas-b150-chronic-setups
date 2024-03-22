from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi.remote import *
from pyBehavior.interfaces.ni import *
from pyBehavior.interfaces.socket import Position
from pyBehavior.interfaces.socket import EventstringSender


class OPENFIELD_LINEAR(SetupGUI):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.sock = None
        self.buildUI()

    # def start_protocol(self):
    #     status = self.client.run_command('toggle_auto_fill', {'on': True})
    #     assert status == 'SUCCESS\n', "Unable to start autofill"
    #     super(OPENFIELD_LINEAR, self).start_protocol()

    def buildUI(self):

        self.ev_logger = EventstringSender()
        self.layout.addWidget(self.ev_logger)
        self.position = Position()
        self.position.new_position.connect(self.register_pos)
        self.position.start()
        self.layout.addWidget(self.position)

        self.pump1 = PumpConfig(self.client, 'pump1', ['module1', 'module2'])
        self.layout.addWidget(self.pump1)

        self.mod1 = RPIRewardControl(self.client, 'module1')
        self.mod1.new_licks.connect(lambda x: self.register_lick('a', x))
        self.mod2 = RPIRewardControl(self.client, 'module2')
        self.mod2.new_licks.connect(lambda x: self.register_lick('b', x))

        self.reward_modules.update({'a': self.mod1, 
                                    'b': self.mod2})

        #format widgets
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(self.mod1)
        mod_layout.addWidget(self.mod2)
        self.layout.addLayout(mod_layout)

    def register_lick(self, arm, amt):
        if self.running:
            self.state_machine.handle_input({"type": "lick", "arm": arm, "amt":amt})
        self.log(f"{arm} {amt} licks", trigger_event=False)

    def register_pos(self, pos):
        pos = tuple(pos)
        self.pos.setText(str(pos))
        if self.running:
            self.state_machine.handle_input({"type":"pos", "pos": pos})
    
    def log(self, msg, trigger_event = True):
        if trigger_event:
            digital_write(self.mapping.loc['event0'], True)
        self.ev_logger.send(msg)
        super(OPENFIELD_LINEAR, self).log(msg)
        if trigger_event:
            digital_write(self.mapping.loc['event0'], False)