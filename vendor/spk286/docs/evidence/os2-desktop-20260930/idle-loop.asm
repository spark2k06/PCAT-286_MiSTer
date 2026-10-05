00003300  06                push es
00003301  60                pusha
00003302  E8B1F4            call 0x27b6
00003305  33C0              xor ax,ax
00003307  E80900            call 0x3313
0000330A  83FC00            cmp sp,byte +0x0
0000330D  61                popa
0000330E  07                pop es
0000330F  1F                pop ds
00003310  C3                ret
00003311  6A08              push byte +0x8
00003313  68F00B            push word 0xbf0
00003316  1F                pop ds
00003317  36A1CEF9          mov ax,[ss:0xf9ce]
0000331B  0BC0              or ax,ax
0000331D  7514              jnz 0x3333
0000331F  FA                cli
00003320  E836F0            call 0x2359
00003323  FB                sti
00003324  7540              jnz 0x3366
00003326  FB                sti
00003327  E89CF9            call 0x2cc6
0000332A  F606D40EFF        test byte [0xed4],0xff
0000332F  74F5              jz 0x3326
00003331  EBEC              jmp short 0x331f
00003333  36A1D4F9          mov ax,[ss:0xf9d4]
00003337  0BC0              or ax,ax
00003339  75E4              jnz 0x331f
0000333B  36FF0ED4F9        dec word [ss:0xf9d4]
00003340  36A19CF9          mov ax,[ss:0xf99c]
00003344  8EC0              mov es,ax
00003346  36A1DEFF          mov ax,[ss:0xffde]
0000334A  368B2EBEF9        mov bp,[ss:0xf9be]
0000334F  3BE8              cmp bp,ax
00003351  7406              jz 0x3359
00003353  26838E940402      or word [es:bp+0x494],byte +0x2
00003359  268BAE1004        mov bp,[es:bp+0x410]
0000335E  0BED              or bp,bp
