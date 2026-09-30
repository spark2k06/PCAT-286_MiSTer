0000331F  FA                cli
00003320  E836F0            call 0x2359
00003323  FB                sti
00003324  7540              jnz 0x3366
00003326  FB                sti
00003327  E89CF9            call 0x2cc6
0000332A  F606D40EFF        test byte [0xed4],0xff
0000332F  74F5              jz 0x3326
00003331  EBEC              jmp short 0x331f
