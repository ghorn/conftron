## This file is part of conftron.  
## 
## Copyright (C) 2011 Matt Peddie <peddie@jobyenergy.com>
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


############  LCM  ###############
eml_lcm_send_template = """\
function %(classname)s_lcm_send_%(type)s( %(type)s_in_ ) %%#eml

%(type)s_ = %(type)s( %(type)s_in_, [1,1] );

if isempty(eml.target)
    %% Executing in MATLAB
    %% do nothing for now  
else
    %% simulating in Embedded MATLAB.
    eml.ceval('%(classname)s_lcm_send_%(type)s', eml.rref(%(type)s_));
end

end
"""

eml_lcm_send_dummy_template = """\
function %(classname)s_lcm_send_%(type)s( %(type)s_in_ ) %%#eml

%% dummy file to keep simulink from choking

end
"""

#############  STRUCTS  #################
eml_constructor_template = ["""\
function %(type)s_out_full_ = %(type)s(%(type)s_in_, n) %%#eml

%% constructor:
""",
"""
if nargin == 0
    %(type)s_out_full_ = %(type)s_out_;
    return;
end

%% safecopy:
if nargin == 1
    n = [1,1];
end

assert(isequal(size(%(type)s_in_), n));

%(type)s_out_full_ = repmat( %(type)s_out_, n );

for k=1:prod(n)
""",
"""\
end

end\
"""]


#################  ENUMS  ####################
eml_enum_constructor_template = ["""\
classdef(Enumeration) %(type)s < int32
    enumeration
""",
"""\
    end
end
"""]
