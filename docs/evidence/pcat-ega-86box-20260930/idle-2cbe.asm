00002CBE  1F                pop ds
00002CBF  F9                stc
00002CC0  C3                ret
00002CC1  0000              add [bx+si],al
00002CC3  006A08            add [bp+si+0x8],ch
00002CC6  1E                push ds
00002CC7  68F00B            push word 0xbf0
00002CCA  1F                pop ds
00002CCB  F706820A0900      test word [0xa82],0x9
00002CD1  741D              jz 0x2cf0
00002CD3  50                push ax
00002CD4  0F01E0            smsw ax
00002CD7  D1E8              shr ax,1
00002CD9  7305              jnc 0x2ce0
00002CDB  E81400            call 0x2cf2
00002CDE  EB0F              jmp short 0x2cef
00002CE0  06                push es
00002CE1  E8B7EB            call 0x189b
00002CE4  68F00B            push word 0xbf0
00002CE7  1F                pop ds
00002CE8  E80700            call 0x2cf2
00002CEB  E8C3EA            call 0x17b1
00002CEE  07                pop es
00002CEF  58                pop ax
00002CF0  1F                pop ds
00002CF1  C3                ret
00002CF2  53                push bx
00002CF3  51                push cx
00002CF4  52                push dx
00002CF5  F7                db 0xf7
00002CF6  06                push es
00002CF7  82                db 0x82
