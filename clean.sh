for class in `cat classes.dat`
do 
    rm ${class}.lcm
    rm ${class}_types.h
done

rm -f classes.dat &>/dev/null
rm -f auto/*.c auto/*.h &>/dev/null
rm -rf java/* &>/dev/null
rm -f octave/lcm_send/*.m &>/dev/null
rm -f octave/lcm_send_dummy/*.m &>/dev/null
rm -f octave/constructors/*.m &>/dev/null
rm -f octave/telemetry/*.m &>/dev/null
rm -f octave/settings/*.m &>/dev/null
rm -f octave/settings_dummy/*.m &>/dev/null
rm -f octave/emlc_c_wrappers/*.c &>/dev/null
rm -f octave/emlc_c_wrappers/*.h &>/dev/null
rm -f octave/enum_decoders/*.h &>/dev/null
rm -f octave/enum_encoders/*.h &>/dev/null
rm -rf python/*
rm -f telemetry/*.c telemetry/*.h &>/dev/null
rm -f settings/*.c settings/*.h
rm -f airframes/*.h
rm -f stubs/*.c stubs/*.o
rm -f lib/*.a &>/dev/null
rm -f *_settings.h
rm -f *_telemetry.h *_telemetry.c &>/dev/null
rm -f lcm_telemetry_auto.h lcm_settings_auto.h
rm -f *.a *.o *~ *.s *.pyc &>/dev/null

