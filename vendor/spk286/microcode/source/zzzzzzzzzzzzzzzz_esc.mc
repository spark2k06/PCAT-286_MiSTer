# CPU-side NPX checks for the standalone no-coprocessor profile.
# ESC tests EM || TS before acquiring ModR/M/displacement; a successful
# check consumes syntax only. WAIT tests MP && TS with BUSY inactive.
microcode_format 26

instruction ESC_NO_COPROCESSOR:
    CHECK_NPX_ESC
    DECODE_MODRM
    END

instruction WAIT_NO_COPROCESSOR:
    CHECK_NPX_WAIT
    END
