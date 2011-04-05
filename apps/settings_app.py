#!/usr/bin/env python

## This file is part of conftron.  
## 
## Copyright (C) 2011 Greg Horn <ghorn@stanford.edu>
## 
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
## 02110-1301, USA.

import wxversion
wxversion.select("2.8")
import wx, wx.html
import sys
from xml.etree import ElementTree as ET
import xml.parsers.expat as expat
import os
import select
import threading
import lcm

ap_project_root = os.environ.get('AP_PROJECT_ROOT')
if ap_project_root == None:
    raise NameError("please set the AP_PROJECT_ROOT environment variable to use Conftron driver")
sys.path.append( ap_project_root+"/conftron" )
sys.path.append( ap_project_root+"/conftron/python" )

import configuration, structs

class LcmListener(threading.Thread):
    def __init__(self, lc, lc_reading_event):
        threading.Thread.__init__(self)
        self.lc = lc
        self.lc_reading_event = lc_reading_event

    def run(self):
        while True:
            if len(select.select([self.lc], [],[])[0]) != 0:
                self.lc_reading_event.clear()
                wx.CallAfter(self.lc.handle)
                # wait for the handler to finish
                self.lc_reading_event.wait()

# this is a group of TextSliders
class TextSliderGroup(wx.BoxSizer):
    def __init__(self, guipage, lc, setting, lc_event):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        
        self.lc = lc
        self.lc_event = lc_event
        self.name = setting['name']
        self.message = setting['setting_struct']['to_python']()
        self.decoder = setting['setting_struct']['to_python']()

        self.text_sliders = []
        for field in setting['fields']:
            ts = TextSlider(guipage, self.message, field)
            self.Add(ts, 0, wx.EXPAND)
            self.text_sliders.append(ts)

        self.set_channel = setting['classname']+"_"+setting['type']+"_"+setting['varname']+"_set"
        ack_channel = setting['classname']+"_"+setting['type']+"_"+setting['varname']+"_ack"

        self.subscription = self.lc.subscribe(ack_channel, self.lc_handler)

    def commit_button_callback(self, event):
        self.lc.publish(self.set_channel, self.message.encode())

    def lc_handler(self, channel, data):
        ap_message = self.decoder.decode(data)
        for ts in self.text_sliders:
            ts.update_ap_value(ap_message)
        # free thread lock
        self.lc_event.set()

# this is one "line" or "entry" in the list of settings
class TextSlider(wx.BoxSizer):
    def slider_to_value(self):
        return self.range[self.slider.GetValue()]

    def value_to_slider(self, value):
        if isinstance(self.field['field_struct'], structs.LCMEnum):
            return self.range.index(value)
        else:
            return self.range.index(min(self.range,key=lambda x:abs(x-float(value))))

    def __init__(self, frame, message, field):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.frame = frame
        self.field = field
        self.message = message

        if isinstance(self.field['field_struct'], structs.LCMEnum):
            # enums
            self.range = self.field['field_struct']['fields']
            self.N = len(self.range)
        else:
            # non-enums
            _min = eval(self.field['min'])
            _max = eval(self.field['max'])
            _step = eval(self.field['step'])
    
            if isinstance( _min, int) and isinstance( _max, int) and isinstance( _step, int) and (_max - _min) % _step == 0:
                self.range = range( _min, _max + 1, _step )
                self.N = len(self.range)
            else:
                self.N = int(round((_max - _min)/_step + 1))
                self.range = [ _min + float(k)*(_max - _min)/(self.N - 1.0) for k in range(0,self.N)]

        position = (0,0)
        size = (300,20)
        style = wx.SL_HORIZONTAL # | wx.SL_AUTOTICKS

        # set up attributes
        self.slider = wx.Slider(self.frame, -1, self.value_to_slider(self.field['default']), 0, self.N - 1, position, size, style)
        self.slider.SetPageSize(1)
        self.potential_value_text = wx.TextCtrl(self.frame, -1, "")
        self.name_text = wx.StaticText(self.frame, -1, self.field['name'])
        self.current_value_text = wx.TextCtrl(self.frame, -1, "", style=wx.TE_READONLY)

        # draw current text
        self.potential_value_text.SetValue(str(self.slider_to_value()))
        self.current_value_text.SetValue('???')

        # callback
        self.frame.Bind(wx.EVT_SLIDER, self.slider_update, self.slider)
        self.frame.Bind(wx.EVT_TEXT, self.text_update, source=self.potential_value_text)

        self.set_message_attribute( self.message, self.field['name'], self.slider_to_value() )

        # add objects to sizer
        self.Add(self.current_value_text, 0 )
        self.Add(self.potential_value_text, 0 )
        self.Add(self.slider, 0 )
        self.Add(self.name_text, 0 )

    def update_ap_value(self, ap_message):
        self.current_value_text.SetValue(str(self.get_message_attribute(ap_message, self.field['name'])))

    def slider_update(self, event):
        val = self.slider_to_value()
        # first unbind text handler to avoid the signal bouncing back and forth
        self.frame.Unbind(wx.EVT_TEXT, source=self.potential_value_text)
        self.potential_value_text.SetValue(str(val))
        self.frame.Bind(wx.EVT_TEXT, self.text_update, source=self.potential_value_text)
        self.set_message_attribute(self.message, self.field['name'], val)

    def text_update(self, event):
        val = self.potential_value_text.GetValue()
        if val == '':
            return
        evalval = eval(val)
        if isinstance( evalval, float) or isinstance( evalval, int):
            self.slider.SetValue(self.value_to_slider(evalval))
            self.set_message_attribute(self.message, self.field['name'], evalval)

    def get_message_attribute(self, message, fieldname):
            names = fieldname.split('.',1)

            if len(names) == 1:
                if isinstance(self.field['field_struct'], structs.LCMEnum):
                    enum_struct = getattr( message, fieldname )
                    return self.field['field_struct']['fields'][getattr( enum_struct, 'val')]
                else:
                    return getattr( message, fieldname )
            else:
                return self.get_message_attribute(getattr(message,names[0]), names[1])


    def set_message_attribute(self, message, fieldname, value):
            names = fieldname.split('.',1)

            if len(names) == 1:
                if isinstance(self.field['field_struct'], structs.LCMEnum):
                    enum_struct = getattr( message, fieldname )
                    setattr( enum_struct, 'val', self.field['field_struct']['fields'].index(value) )
                else:
                    setattr( message, fieldname, value )
            else:
                self.set_message_attribute(getattr(message,names[0]), names[1], value)



class GuiPage(wx.ScrolledWindow):
    def __init__(self, notebook, lc, settings, lc_event):
        wx.ScrolledWindow.__init__(self, notebook, -1)
        self.settings = settings

        # set up structandbutton groups
        top_sizer = wx.BoxSizer(wx.VERTICAL)

        for s in self.settings:
            v_sizer = wx.BoxSizer(wx.VERTICAL)
            slider_group = TextSliderGroup(self, lc, s, lc_event)
            button = wx.Button(self, label = "commit", size=(160,30))
            self.Bind(wx.EVT_BUTTON, slider_group.commit_button_callback, button)

            # name and commit button
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            name_text = wx.StaticText(self, -1, s['name'])
            h_sizer.Add(button, 0)
            h_sizer.Add(name_text, 0, wx.ALIGN_CENTER | wx.LEFT, 25)

            v_sizer.Add(h_sizer, 0)
            v_sizer.Add(slider_group, 5, wx.BOTTOM, 20)
            
            top_sizer.Add(v_sizer)
        
            s['subscription'] = slider_group.subscription

        # Layout the top_sizer
        top_sizer.Fit(self)
        self.SetSizer(top_sizer)
        self.SetScrollbars(0,50,0,500)
        self.SetAutoLayout(1)

class Frame(wx.Frame):
    def unsubscribe_all(self):
        # unsubscribe to everything if needed
        if hasattr(self, 'settings'):
            for s in self.settings:
                self.lc.unsubscribe(s['subscription'])

    def reset(self):

        self.unsubscribe_all()

        # make conf
        self.conf = configuration.Configuration(self.aircraft)

        self.settings = []
        for sc in self.conf.settings:
            for s in sc['settings']:
                if not (s['has_key']('settingsapp') and s['settingsapp'] == "ignore"):
                    self.settings.append(s)

        # if setting doesn't have guipage, set guipage to "unsorted"
        for s in self.settings:
            if not s['has_key']('guipage'):
                s['guipage'] = 'unsorted';
        self.settings.sort( key=lambda x: x['guipage'] )

        # group settings by guipage and add to notebook
        self.notebook = wx.Notebook(self)
        self.guipages = {}

        from itertools import groupby
        for guipage_name, g in groupby(self.settings, lambda s: s['guipage']):
            self.guipages[guipage_name] = GuiPage(self.notebook, self.lc, list(g), self.lc_event)
            self.notebook.AddPage( self.guipages[guipage_name], guipage_name)


    def __init__(self, title, aircraft):
        wx.Frame.__init__(self, None, title=title, pos=(150,150), size=(650,500))

        self.aircraft = aircraft

        # set up lcm
        self.lc = lcm.LCM("udpm://239.255.76.67:7667?ttl=0")

        self.lc_event = threading.Event()

        self.reset()

        # start the lcm listener thread
        self.lcm_listener_thread = LcmListener(self.lc, self.lc_event)
        self.lcm_listener_thread.daemon = True # so that it dies when the program stops
        self.lcm_listener_thread.start()

        self.Show()



if not sys.argv[1]:
    print "please call settings_app.py with the name of the aircraft, e.g. wing7 or m5"
    exit(1)

app = wx.App(redirect=False)   # Error messages go to popup window
top = Frame("Conftron Mex-o-set", sys.argv[1])
top.Show(True)
app.MainLoop()
