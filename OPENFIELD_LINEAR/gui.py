from PyQt5.QtWidgets import  QHBoxLayout
from pyBehavior.gui import *
from pyBehavior.interfaces.rpi import *
import socket
import time
import ast
import numpy as np

class OPENFIELD_LINEAR(SetupGUI):

    def __init__(self):
        super(OPENFIELD_LINEAR, self).__init__(Path(__file__).parent.resolve())
        self.sock = None
        
        self.buildUI()
        self.client.run_command('toggle_auto_fill', {'on': True})

    def buildUI(self):

        port_layout = QHBoxLayout()
        ip = QLabel(f"IP: {socket.gethostbyname(socket.gethostname())}")
        self.pos_port = QLineEdit()
        self.pos_port.setValidator(QDoubleValidator())
        self.pos_port.textChanged.connect(self.bind_port)
        self.pos_port.setText("1234")
        port_layout.addWidget(ip)
        port_layout.addWidget(self.pos_port)
        self.layout.addLayout(port_layout)

        pos_layout =  QHBoxLayout()
        poslabel = QLabel("Position")
        self.pos = QLabel("")
        pos_layout.addWidget(poslabel)
        pos_layout.addWidget(self.pos)
        self.layout.addLayout(pos_layout)


        self.pump1 = PumpConfig(self.client, 'pump1')
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

        self.pos_thread = Position(self)
        self.pos_thread.start()
    
    def bind_port(self, port):
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", int(port)))

    def register_lick(self, data, module):
        msg = f'{module} lick {data}'
        self.log(msg)

    def register_pos(self, pos):
        pos = tuple(pos)
        self.pos.setText(str(pos))
        if self.running:
            self.state_machine.handle_input(pos)

class Position(QThread):
    def __init__(self, parent, buff_size = 10):
        super(Position, self).__init__()
        self.parent = parent
        self.pos_buffer = []
        self.conf_buffer = []
    
    def run(self):
        while True:
            if self.parent.sock:
                pos = ast.literal_eval(self.parent.sock.recv(1024).decode())
                self.pos_buffer.append(np.array([i[0] for i in pos[0]]))
                self.conf_buffer.append(np.array([i[1] for i in pos[0]]))
                self.pos_buffer = self.pos_buffer[-5:]
                self.conf_buffer = self.conf_buffer[-5:]
                weighted_pos = np.array(self.pos_buffer) * np.array(self.conf_buffer)[:,:,None]
                pos = weighted_pos.sum(axis=0)/np.array(self.conf_buffer).sum(axis=0)[:,None]
                pos = pos.mean(axis=0).tolist()
                self.parent.register_pos(pos)
                # time.sleep(.05)