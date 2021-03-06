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

## Init settings
lcm_settings_init_template = """
void
%(varname)s_settings_init(const char *provider)
{
  %(classname)s_lcm_init(provider);
  %(classname)s_lcm_subscribe_chan(%(type)s, &%(classname)s_%(varname)s_setter, NULL, "%(classname)s_%(type)s_%(varname)s_set");
  %(classname)s_lcm_subscribe_chan(%(type)s, &%(classname)s_%(varname)s_resetter, NULL, "%(classname)s_%(type)s_%(varname)s_reset");
  %(classname)s_lcm_subscribe_chan(%(type)s, &%(classname)s_%(varname)s_query, NULL, "%(classname)s_%(type)s_%(varname)s_query");
}
"""

lcm_settings_init_custom_chan_template = """
void
%(varname)s_settings_init(const char *provider)
{
  %(classname)s_lcm_init(provider);
  %(classname)s_lcm_subscribe_chan(%(type)s, &%(classname)s_%(varname)s_setter, NULL, "%(channel)s");
}
"""

lcm_settings_init_nop_template = """
void
%(varname)s_settings_init(const char *provider __attribute__((unused)))
{
  return;
}
"""

lcm_settings_set_nop_template = """
void
%(classname)s_%(varname)s_setter(const lcm_recv_buf_t *rbuf __attribute__((unused)),  
                                      const char *channel __attribute__((unused)),
                                      const %(classname)s_%(type)s *msg __attribute__((unused)),
                                      void *user __attribute__((unused)))
{
  return;
}
"""

lcm_settings_init_prototype = """\
void %(varname)s_settings_init(const char *provider); 
"""

lcm_settings_init_call_template = """  %(varname)s_settings_init(provider); \\"""
lcm_settings_init_null_template = """  %(classname)s_%(varname)s_setter(NULL, NULL, NULL, NULL); \\"""

lcm_settings_init_class_template = """
/* Initialize all the LCM classes and set all settings values to their
   default values as defined in XML */
#define %(classname)s_settings_init(provider) {      \\
%(init_calls)s
%(null_calls)s
}
"""

lcm_init_all_template = """
/* Initialize all the LCM classes and set all settings values to their
   default values as defined in XML */
#define settings_init(provider) {      \\
%(init_calls)s }
"""

## Run settings
lcm_settings_prototype = """
void %(classname)s_%(varname)s_setter(const lcm_recv_buf_t *rbuf,  
                                      const char *channel,
                                      const %(classname)s_%(type)s *msg,
                                      void *user);
"""

lcm_settings_reset_template = """
static void 
%(classname)s_%(varname)s_resetter(const lcm_recv_buf_t *rbuf __attribute__((unused)),
                                const char *channel __attribute__((unused)),
                                const %(classname)s_%(type)s *new_data __attribute__((unused)),
                                void *user __attribute__((unused)))
{
"""+lcm_settings_init_null_template.rstrip('\\')+"""
}
"""

lcm_settings_query_template = """
static void 
%(classname)s_%(varname)s_query(const lcm_recv_buf_t *rbuf __attribute__((unused)),
                                const char *channel __attribute__((unused)),
                                const %(classname)s_%(type)s *new_data __attribute__((unused)),
                                void *user __attribute__((unused)))
{
  %(classname)s_lcm_send_chan(&%(varname)s, %(type)s, "%(classname)s_%(type)s_%(varname)s_ack");
}
"""


lcm_settings_func_template = """
void 
%(classname)s_%(varname)s_setter(const lcm_recv_buf_t *rbuf __attribute__((unused)),  
                                 const char *channel __attribute__((unused)),                 
                                 const %(classname)s_%(type)s *new_data,                                      
                                 void *user __attribute__((unused)))
{
%(field_settings)s
  %(classname)s_lcm_send_chan(&%(varname)s, %(type)s, "%(classname)s_%(type)s_%(varname)s_ack");
}
"""

lcm_settings_field_template_mm = """
  if (new_data == NULL) {
    %(varname)s.%(name)s = %(default)s;
  } else {
    if (new_data->%(name)s > %(max)s)
      %(varname)s.%(name)s = %(max)s;
    else if (new_data->%(name)s < %(min)s)
      %(varname)s.%(name)s = %(min)s;
    else
      %(varname)s.%(name)s = new_data->%(name)s;
  }
"""

lcm_settings_field_enum_template_mm = """
  // enum
  if (new_data == NULL) {
    %(varname)s.%(name)s = %(default)s;
  } else {
    if (new_data->%(name)s.val > %(max)s || new_data->%(name)s.val < %(min)s){
      printf("conftron settings enum %(varname)s.%(name)s received out of bounds value (%%d)\\n", new_data->%(name)s.val);
      exit(1);
    }
    %(varname)s.%(name)s = (%(field_type)s) new_data->%(name)s.val;
  }
"""

lcm_send_settings_template = """
void
%(classname)s_%(varname)s_set(%(classname)s_%(type)s *new_data)
{
  %(classname)s_lcm_send(new_data, %(type)s);
}
"""

lcm_check_all_template = """
#define settings_check() { \\
%(run_calls)s }
"""

lcm_check_call_template = """
#define %(classname)s_settings_check() { \\
  lcm_check(%(classname)s_lcm.lcm, %(classname)s_lcm.fd);  \\
}
"""

## Parsing errors
parse_settings_nobounds = """
Error: Settings generation couldn't derive a set of bounds 
for field `%(f)s' in section `%(s)s'.  

Make sure you've specified either a `max' and `min' value or an
`absmax' for symmetric zero-mean bounds.
""" 

parse_settings_noval = """
Error: Settings generation couldn't derive a(n) `%(tag)s' value for
field `%(name)s' in section `%(parentname)s'.

You must specify this value either for the entire section or for each
field within the section.  (If both are specified, the value inside
the field tag will take precedence.)
"""

parse_settings_badval = """
Error: Settings generation received a(n) `%(sp)s' value of `%(val)s'
for field `%(f)s' in section `%(s)s'.  This value doesn't make sense
given the specified bounded range of [%(min)s, %(max)s].
"""

## emlc
emlc_settings_template = ["""\
function %(varname)s_out_ = %(classname)s_setting_%(type)s_%(varname)s(%(varname)s_in_) %%#eml

if nargin == 1
    %(varname)s_out_ = %(type)s(%(varname)s_in_);
    return;
end

%(varname)s_out_ = %(type)s();
""",
"""
if isempty(eml.target)
    %% Executing in MATLAB
    %% fill in defaults
""",
"""\
else
    %% simulating in Embedded MATLAB
    %% use the lcm c function
    eml.ceval('%(classname)s_get_setting_%(type)s_%(varname)s', eml.wref(%(varname)s_out_) );
end

end\
"""]

emlc_settings_get_setting_c_wrapper_template = ["""\
void %(classname)s_get_setting_%(type)s_%(varname)s( void * setting_ext)""","""{
  memcpy( setting_ext, &%(varname)s, sizeof(%(type)s));
}
"""]
