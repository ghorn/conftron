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

import genconfig, baseio
from eml_structs_templates import *

lcm_primitives = ["double", "float", "int32_t", "int16_t", "int8_t"]

class StructField(baseio.TagInheritance):
    def __init__(self, attrib, parent):
        self.__dict__.update(attrib)
        self._inherit(parent)
        if self.has_key('array'):
            self.sizes = self.array.rsplit(",")

    def to_cstring(self):
        # handle pointers
        ptr = None
        if self.has_key('ptr'):
            ptr = self.ptr.count('*')
            if ptr == 0 and self.has_key('ptr'):
                ptr = int(self.ptr)
        # field name
        fstr = self.type + " " + self.name
        if ptr: fstr += '[1]'*ptr 
        # handle arrays
        if self.has_key('array'):
            for s in self.sizes:
                fstr += "[" + s + "]"
        fstr += ";"
        # comments and units (appended to comment)
        if self.has_key('comment') or self.has_key('unit'):
            fstr += "\t\t" + "// "
        if self.has_key('unit'):
            fstr += "(" + self.unit + ") -- "
        if self.has_key('comment'):
            fstr += self.comment
        fstr += "\n"
        return fstr

    def to_lcm_callback(self, prefix=""):
        if self.has_key('array'):
            return self.to_lcm_callback_array(prefix)
        else:
            return self.to_lcm_callback_single(prefix)

    def to_lcm_callback_single(self, prefix):
        """Creates a function `return_primitive' that returns a flat
        array of (name, value) pairs.  `name' indicates what's being
        plotted; `value' is the part of the message that goes with
        that name (e.g. a struct member or array element).
        `return_array' takes an lcm message as an argument.
        """
        if self.type in lcm_primitives:
            def return_primitive(msg):
                return [(prefix + self.name, msg)]
            return return_primitive
        else:
            nextfn = self.cl.make_lcm_callback(self.type, prefix + self.name + "_")
            def return_primitive(msg):
                return nextfn(msg)
            return return_primitive

    def lcm_unroll_array(self, name, sizes):
        """Creates a flat array of (name, function) pairs.  `name' is
        the correct field label, e.g. e2u_P_27 for e2u.P[2][7], and
        `function' returns the specified element (e.g. [2][7]) from a
        message (passed as its argument).
        """
        ## Guido is on my shit list today.  Values you loop over (`n'
        ## in this case) are fixed in value only at the end of the
        ## loop scope?  I WANT MY LET OVER LAMBDA, YOU ASSHOLE!
        if len(sizes) == 1:     
            out = []
            for n in xrange(int(sizes[0])):
                out.append((name + "_" + str(n), lambda msg, msgidx=n: msg[msgidx]))
            return out
        else:
            arrout = []
            for n in xrange(int(sizes[0])):
                unroll = self.lcm_unroll_array(name + "_" + str(n), sizes[1:])
                arrout.extend([((lambda c=n: c)(), ur) for ur in unroll])
            return [(pr[0], lambda msg, c=n, pv=pr: pv[1](msg[c])) for n, pr in arrout]
                
    def to_lcm_callback_array(self, prefix):
        """Creates a function `return_array' that returns a flat array
        of (name, value) pairs.  `name' indicates what's being
        plotted; `value' is the part of the message that goes with
        that name (e.g. a struct member or array element).
        `return_array' takes an lcm message as an argument.
        """
        arrlambda = self.lcm_unroll_array(prefix + self.name, self.sizes)
        if self.type in lcm_primitives:
            def return_array(msg):
                out = [(pr[0], pr[1](msg)) for pr in arrlambda]
                return out
            return return_array
        else:
            nextfns = [(self.cl.make_lcm_callback(self.type, pr[0]+"_"), pr[1]) for pr in arrlambda]
            def return_array(msg):
                out = []
                [out.extend(nextfun(unpack(msg))) for nextfun, unpack in nextfns]
                return out
            return return_array

class LCMStruct(baseio.TagInheritance, baseio.IncludePasting, baseio.OctaveCode):
    """This is the native format for structs we need to use.  You can
    convert to and from XML, C, LCM and Python."""
    def __init__(self, msg, parent):
        self.__dict__.update(msg.attrib)
        self._inherit(parent)
        self.parent = parent
        self._filter_fields(msg.getchildren())
        self.classname = parent.name
        self.type = self.name
        self.lcm_folder = genconfig.lcm_folder

    def to_lcm_callback(self, prefix=""):
        member_callbacks = [(m, m.to_lcm_callback(prefix)) for m in self.members]
        def return_data(msg):
            fields = []
            [fields.extend(mc(getattr(msg, m.name))) for m, mc in member_callbacks]
            return fields
        return return_data

    def _filter_fields(self, fields):
        die = 0
        outstructs = []
        flattened = self.insert_includes(fields, ['field', 'member'])
        self.check_includes(flattened, ['field', 'member'])
        outstructs = [StructField(dict(f.attrib, **{'cl':self.parent}), self) for f in flattened]
        die = sum([s.die for s in outstructs])
        if die:
            print "Lots of types errors detected in struct `%(name)s'; cannot continue code generation." % self
            sys.exit(1)
        self.members = outstructs

    def to_c(self):
        """This emits additional C code (struct definitions) for all
        the messages described, plus the #define-d enum contents since
        LCM doesn't implement enum types."""
        outstr = ""
        if self.has_key('__base__'):
            outstr += "#ifndef " + self.name.upper() + "\n"
            outstr += "#define " + self.name.upper() + "\n"
        outstr += "typedef struct " + self.name + " {\n" # self.classname + "_" + 
        if self.has_key('comment'):
            outstr += "/* " + self.comment + " */\n"
        for m in self.members: 
            outstr += "  " + m.to_cstring()
        outstr += "} " + self.name + ";\n" # + self.classname + "_" 
        if self.has_key('__base__'):
            outstr += "#endif // " + self.name.upper() + "\n"
        return outstr
        
    def to_lcm(self):
        """This emits the LCM configuration file based on the structs
        described in XML."""
        outstr = "struct " + self.name + " {\n" # self.classname + "_" + 
        if self.has_key('comment'):
            outstr += "/* " + self.comment + " */\n"
        for m in self.members: 
            outstr += "  " + m.to_cstring()
        outstr += "}\n"
        return outstr

    def to_eml(self):
        octave_primitives_map = {'double':'double', 'float':'double', 'int8_t':'int8', 'int16_t':'int16', 'int32_t':'int32'}
 
        def lcm_send_output_f(cf):
            cf.write(eml_lcm_send_template % self)

        def lcm_send_dummy_output_f(cf):
            cf.write(eml_lcm_send_dummy_template % self)

        def constructor_output_f(cf):
            cf.write(eml_constructor_template[0] % self)
            for m in self.members:
                ## THIS DOES NOT BELONG HERE:
                ## give them all an octave-compatible array
                ## i.e. scalar -> [1,1], vector -> [n,1], multidimensional array -> (no change)
                if not m['has_key']('array'):
                    m['octave_array']="1,1"
                else:
                    split_array = m['array'].split(",")
                    if len(split_array) == 1:
                        m['octave_array'] = split_array[0]+",1"
                    else:
                        m['octave_array'] = m['array']

                ## loop though members and write their individual constructors
                if m['type'] in octave_primitives_map.keys():
                    # primitives
                    m['octave_type'] = octave_primitives_map[m['type']]
                    cf.write(self.type+"_out_.%(name)s = %(octave_type)s(zeros([%(octave_array)s]));\n" % m)
                else:
                    # not primitives
                    cf.write(self.type+"_out_.%(name)s = repmat(emlc_%(type)s(), [%(octave_array)s]);\n" % m)

            cf.write(eml_constructor_template[1] % self)

            ## loop though and safely copy each member
            for m in self['members']:
                if m['type'] in octave_primitives_map.keys(): # primitive type
                    cf.write(("    "+self.type+"_out_full_(k).%(name)s = "+self.type+"_in_(k).%(name)s;\n") % m)
                else: # non-primitive type
                    if m['has_key']('array'): # arrays
                        cf.write(("    "+self.type+"_out_full_(k).%(name)s = "+self.classname+"_%(type)s("+self.type+"_in_(k).%(name)s, [%(array)s]));\n") % m)
                    else: # scalars
                        cf.write(("    "+self.type+"_out_full_(k).%(name)s = "+self.classname+"_%(type)s("+self.type+"_in_(k).%(name)s, [1,1]);\n") % m)
            cf.write(eml_constructor_template[2] % self)

        self.to_octave_code('octave/lcm_send/'+self['classname']+'_lcm_send_'+self['type'], lcm_send_output_f)
        self.to_octave_code('octave/lcm_send_dummy/'+self['classname']+'_lcm_send_'+self['type'], lcm_send_dummy_output_f)
        self.to_octave_code('octave/constructors/'+self['classname']+'_'+self['type'], constructor_output_f)

    def to_include(self):
        pass
        
    def to_python(self):
        """This emits The LCM Python class"""

        # import the class modules, like ap/sim/vis/etc
        class_module = __import__(self['classname'])
        return getattr(class_module, self['type'])()

class LCMEnum(baseio.TagInheritance, baseio.OctaveCode):
    def __init__(self, enum, parent):
        self.__dict__.update(enum.attrib)
        self.fields = [f.strip() for f in self.fields.rsplit(',')]
        self.classname = parent.name
        self.type = self.name
        self._inherit(parent)
        self.lcm_folder = genconfig.lcm_folder

    def to_lcm_callback(self, prefix=""):
        def cb(msg):
            return [(prefix + self.name, msg.val)]
        return cb

    def get_fields_with_indices(self):
        return dict(zip(self.fields, range(len(self.fields))))
    
    def get_indices_with_fields(self):
        return dict(zip(range(len(self.fields)), self.fields))

    def to_c(self):
        estr = ""
        if self.has_key('comment'):
            estr += "/* " + self.comment + " */\n"
        if self.has_key('__base__'):
            estr += "#ifndef " + self.name.upper() + "\n"
            estr += "#define " + self.name.upper() + "\n"
        estr += "typedef " 
        estr += "enum {\n"
        for (k,f) in enumerate(self.fields):
            estr += "  " + f + " = "+str(k)+",\n"
        estr += "} "
        if self.has_key('typedef'):
            estr += self.typedef
        else:
            estr += self.name
        estr += ";\n"
        if self.has_key('__base__'):
            estr += "#endif // " + self.name.upper() + "\n"
        return estr

    def to_c_defines(self):
        """We use #defines to implement a hacky enum.  Simply typedef
        int to command_t and use the preprocessor values.  The
        autogenerated code takes care of the rest.  This means that
        you still have to extract the "val" field or just typecast
        it."""

        estr = ""
        if self.has_key('comment'):
            estr += "/* " + self.comment + " */\n"
        estr += "typedef int " + self.name + ";\n"
        defenum = zip(self.fields, range(len(self.fields)-1))
        for f, n in defenum:
            estr += "#define " + f + " " + str(n) + "\n"
        return estr

    def to_eml(self):
        def lcm_send_output_f(cf):
            cf.write(eml_lcm_send_template % self)

        def lcm_send_dummy_output_f(cf):
            cf.write(eml_lcm_send_dummy_template % self)

        def enum_encoder_output_f(cf):
            cf.write(eml_enum_encoder_template_0 % self)
            for v,k in self['get_indices_with_fields']().iteritems():
                cf.write('    case \''+k+'\'\n')
                cf.write(('        int32_out = int32('+str(v)+');\n') % self)
            cf.write(eml_enum_encoder_template_1 % self)

        def enum_decoder_output_f(cf):
            cf.write(eml_enum_decoder_template_0 % self)
            for v,k in self['get_indices_with_fields']().iteritems():
                cf.write('    case int32('+str(v)+')\n')
                cf.write(('        string_out = \''+k+'\';\n') % self)
            cf.write(eml_enum_decoder_template_1 % self)

        def constructor_output_f(cf):
            cf.write(eml_enum_constructor_template % self)

        self.to_octave_code('octave/lcm_send/'+self['classname']+'_lcm_send_'+self['type'], lcm_send_output_f)
        self.to_octave_code('octave/lcm_send_dummy/'+self['classname']+'_lcm_send_'+self['type'], lcm_send_dummy_output_f)
        self.to_octave_code('octave/constructors/'+self['classname']+'_'+self['type'], constructor_output_f)
        self.to_octave_code('octave/enum_encoders/encode_%(classname)s_%(type)s' % self, enum_encoder_output_f)
        self.to_octave_code('octave/enum_decoders/decode_%(classname)s_%(type)s' % self, enum_decoder_output_f)

    def to_lcm(self):
        estr = "struct " + self.name + " {\n  int32_t val;\n}\n"
        return estr

    def to_include(self):
        pass

    def to_python(self):
        print "Compiling XML directly to python classes is not implemented. --MP"

class CStructClass(baseio.CHeader, baseio.LCMFile, baseio.CCode, baseio.Searchable, baseio.IncludePasting):
    def __init__(self, name, cl, structs, path, filename):
        self.__dict__.update(cl.attrib)
        self.name = name
        self.path = path
        self.file = filename
        self._filter_structs(structs)

    def merge(self, other):
        ## The merge operation breaks a few things to do with internal
        ## consistency.  Basically, when we update the internal
        ## dictionary from the `other' instance, our local tags can be
        ## overwritten.  There's no good way around this within the
        ## current object hierarchy.  However, since the merge
        ## operation is not part of __init__(), the correct tags are
        ## propagated to the children of each instance _before_ they
        ## merge.  Basically, when you use the Configuration API,
        ## search for the properties of the actual object you want to
        ## deal with, and don't assume its parents will tell you what
        ## you want to know about it.

        for k, v in other.__dict__.iteritems():
            if not k in genconfig.reserved_tag_names:
                try:
                    # Is it a method?
                    getattr(getattr(self, k), "__call__")
                except AttributeError:
                    # Nope.
                    self.__dict__[k] = other.__dict__[k]
        self.structs.extend(other.structs)
        return self

    def search(self, searchname):
        return self._search(self.structs, searchname)

    def make_lcm_callback(self, name, prefix=""):
        try: 
            ff = self.search(name)
        except StopIteration: 
            print "Error!  No struct by the name of %(name) in class %(classname)!" % {'name':name, 'classname':self.name}
            return None
        else:
            return ff.to_lcm_callback(prefix)

    def codegen(self):
        self.to_structs_h()
        self.to_structs_lcm()
        [s.to_eml() for s in self.structs]
        self.to_emlc_macro_wrappers()

    def _filter_structs(self, structs):
        die = 0
        outstructs = []
        flattened = self.insert_includes(structs, ['struct', 'message', 'enum'])
        self.check_includes(flattened, ['struct', 'message', 'enum'])
        for s in flattened:
            if s.tag == 'enum':
                outstructs.append(LCMEnum(s, self))
            else:
                outstructs.append(LCMStruct(s, self))
        die = sum([s.die for s in outstructs])
        if die:
            print "Lots of types errors detected; cannot continue code generation."     
            sys.exit(1)
        self.structs = outstructs

    def include_headers(self):
        return "\n".join(["#include \"" + genconfig.lcm_folder + "/" 
                          + self.name + "_" + x.name + 
                          ".h\"\n" for x in self.structs])

    def to_emlc_macro_wrappers(self):
        def structs_f(cf):
            cf.write('#include <emlc_telemetry.h>\n')
            [cf.write("\n#define %(classname)s_lcm_send_%(type)s(msg) %(classname)s_lcm_send(msg, %(type)s)" % m) for m in self.structs]
        self.to_h('octave/emlc_macro_wrappers/'+self.name+'_macro_wrappers', structs_f)


    def to_structs_h(self):
        def structs_f(cf):
            cf.write("#include <stdint.h>\n\n");
            for s in self.structs:
                # print "writing" , s.name
                cf.write(s.to_c())
                cf.write("\n");
        self.to_h(self.name + "_types", structs_f)
        
    def to_structs_lcm(self):
        def structs_f(cf):
            for s in self.structs:
                cf.write(s.to_lcm())
                cf.write("\n")
        self.to_lcm(self.name, structs_f)
    
