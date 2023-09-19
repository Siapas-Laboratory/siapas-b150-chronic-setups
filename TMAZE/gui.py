import logging
import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import  QSpacerItem, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy, QGridLayout, QButtonGroup
from pyBehavior.interfaces.ni import *
from pyBehavior.gui import *
from pathlib import Path



class TMAZE(SetupGUI):

    def __init__(self):
        super(TMAZE, self).__init__(Path(__file__).parent.resolve())
        self.buildUI()

    def buildUI(self):

        # organize beams by corresponding arm of the maze
        right_arm = [f'beam{i}' for i in range(1,9)]
        left_arm = [f'beam{i}' for i in range(9,17)]
        bottom_arm = [f'beam{i}' for i in range(17,28)]
        sleep_arm = ['beam29', 'beam28']

        # get the port mappings for all beams
        all_beams = right_arm + left_arm + bottom_arm + sleep_arm
        self.beams = self.mapping.loc[all_beams].rename("port").to_frame()
        self.beams['state'] = np.zeros((len(self.beams),), dtype = bool)        
        
        # get port mappings for all doors
        door_names = [f'door{i}' for i in range(1,8)]
        self.doors = self.mapping.loc[door_names].rename("port").to_frame()
        # create a grid of buttons representing all beams and doors
        beam_buttons = {}
        self.door_button_group = QButtonGroup(exclusive = False)
        door_buttons = {} 
        grid = QGridLayout()
        
        # fill buttons for the stem arm
        for i, element in enumerate(['door1'] + bottom_arm + ['door3']):
            btn = QPushButton(element)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCheckable(True)
            grid.addWidget(btn, i+1, 10)
            if 'beam' in element: 
                btn.setStyleSheet("""
                QPushButton {
                    border-radius : 1em;  
                    border : 2px solid black 
                }
                QPushButton::checked { 
                    background-color : red;
                }
                """
                )
                beam_buttons.update({element: btn})
            elif 'door' in element:
                self.door_button_group.addButton(btn)
                door_buttons.update({element: btn})

        # fill buttons for the right and left arms
        for i, element in enumerate(['door6'] + right_arm[::-1] + ['door7', '','door5'] + left_arm + ['door4']):
            if element == '':
                grid.addItem(QSpacerItem(0,0,QSizePolicy.Expanding,QSizePolicy.Expanding), 14, i)
            else:
                btn = QPushButton(element)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setCheckable(True)
                grid.addWidget(btn, 14, i)
                if 'beam' in element: 
                    btn.setStyleSheet("""
                    QPushButton {
                        border-radius : 1em;  
                        border : 2px solid black 
                    }
                    QPushButton::checked { 
                        background-color : red;
                    }
                    """
                    )
                    beam_buttons.update({element: btn})
                elif 'door' in element:
                    self.door_button_group.addButton(btn)
                    door_buttons.update({element: btn})
        
        for i, element in enumerate(['door2'] + sleep_arm):
            btn = QPushButton(element)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCheckable(True)
            grid.addWidget(btn, 15+i, 10)
            if 'beam' in element: 
                btn.setStyleSheet("""
                QPushButton {
                    border-radius : 1em; 
                    border : 2px solid black 
                }
                QPushButton::checked { 
                    background-color : red;
                }
                """
                )
                beam_buttons.update({element: btn})
            elif 'door' in element:
                self.door_button_group.addButton(btn)
                door_buttons.update({element: btn})

        self.beams['button'] = pd.Series(beam_buttons)
        self.doors['button'] = pd.Series(door_buttons)
        self.door_button_group.buttonToggled.connect(self.toggle_door)

        # valve widgets
        self.stem_valve = NIRewardControl( self.mapping.loc['juicer_valve2'], 
                                        'juicer_valve2', self,
                                        self.mapping.loc['juicer_purge'],
                                        self.mapping.loc['juicer_flush'],
                                        self.mapping.loc['juicer_bleed1'],
                                        self.mapping.loc['juicer_bleed2'])
        
        self.b_valve = NIRewardControl( self.mapping.loc['juicer_valve3'], 
                                        'juicer_valve3', self,
                                        self.mapping.loc['juicer_purge'],
                                        self.mapping.loc['juicer_flush'],
                                        self.mapping.loc['juicer_bleed1'],
                                        self.mapping.loc['juicer_bleed2'])

        self.a_valve = NIRewardControl( self.mapping.loc['juicer_valve1'], 
                                        'juicer_valve1', self,
                                        self.mapping.loc['juicer_purge'],
                                        self.mapping.loc['juicer_flush'],
                                        self.mapping.loc['juicer_bleed1'],
                                        self.mapping.loc['juicer_bleed2']) 
        
        self.reward_modules.update({'a': self.a_valve, 
                                    'b': self.b_valve, 
                                    's': self.stem_valve})

        #format widgets
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.stem_valve)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.b_valve)
        hlayout.addLayout(grid)
        hlayout.addWidget(self.a_valve)
        vlayout.addLayout(hlayout)
        self.layout.addLayout(vlayout)

        # start digital input threads
        # thread to monitor beams
        self.beam_thread = NIDIChanThread(self.beams.port)
        self.beam_thread.state_updated.connect(self.register_beam_break)
        self.beam_thread.start()

        # thread to monitor licking
        self.lick_thread = NIDIChanThread(self.mapping.loc[["licks_all"]], falling_edge = False)
        self.lick_thread.state_updated.connect(self.register_lick)
        self.lick_thread.start()

        self.trial_lick_n = 0
        self.prev_lick = datetime.now()
        self.bout_thresh = 1

        for i in range(1,8):
            digital_write(self.doors.loc[f"door{i}",'port'], True)
    
    def toggle_door(self, btn, checked):
        door = btn.text()
        if checked:
            self.log(f"rasing {door}")
            digital_write(self.doors.loc[door,'port'], False)
        else:
            self.log(f"lowering {door}")
            digital_write(self.doors.loc[door,'port'], True)

    def register_lick(self, data):
        self.log('lick')
        self.trial_lick_n += 1
        self.prev_lick = datetime.now()
  
    def register_beam_break(self, data):
        changed = data[self.beams.state != data].index
        for c in changed:
            if data.loc[c] > self.beams.loc[c].state:
                self.log(c)
                if self.running:
                    self.state_machine.handle_input(c)
            self.beams.loc[c,'button'].toggle()
        self.beams['state'] = data

    