from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi import *
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
        self.mod2 = RPIRewardControl(self.client, 'module2')
        self.reward_modules.update({'a': self.mod1, 
                                    'b': self.mod2})

        #format widgets
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(self.mod1)
        mod_layout.addWidget(self.mod2)
        self.layout.addLayout(mod_layout)

        # start digital input threads
        # threads to monitor licking
        self.lick1_thread = RPILickThread(self.client, "module1")
        self.lick1_thread.lick_num_updated.connect(lambda x: self.register_lick(x, 'module1'))
        self.lick1_thread.start()

        self.lick2_thread = RPILickThread(self.client, "module2")
        self.lick2_thread.lick_num_updated.connect(lambda x: self.register_lick(x, 'module2'))
        self.lick2_thread.start()

    def register_lick(self, data, module):
        msg = f'{module} lick {data}'
        self.log(msg)

    def register_pos(self, pos):
        pos = tuple(pos)
        self.pos.setText(str(pos))
        if self.running:
            self.state_machine.handle_input(pos)
    
    def log(self, msg):
        digital_write(self.mapping.loc['event0'], True)
        self.ev_logger.send(msg)
        super(OPENFIELD_LINEAR, self).log(msg)
        digital_write(self.mapping.loc['event0'], False)

    def trigger_reward(self, module, small, force = True, wait = False):
        self.reward_modules[module].trigger_reward(small, force, wait)