00002C80  2489              and al,0x89
00002C82  47                inc di
00002C83  02C3              add al,bl
00002C85  6A08              push byte +0x8
00002C87  1E                push ds
00002C88  68F00B            push word 0xbf0
00002C8B  1F                pop ds
00002C8C  50                push ax
00002C8D  0F01E0            smsw ax
00002C90  D0E8              shr al,1
00002C92  58                pop ax
00002C93  7329              jnc 0x2cbe
00002C95  803EAC0EFF        cmp byte [0xeac],0xff
00002C9A  7522              jnz 0x2cbe
00002C9C  803E151200        cmp byte [0x1215],0x0
00002CA1  7419              jz 0x2cbc
00002CA3  3D5F00            cmp ax,0x5f
00002CA6  7416              jz 0x2cbe
00002CA8  60                pusha
00002CA9  06                push es
00002CAA  368B2EDEFF        mov bp,[ss:0xffde]
00002CAF  899EAA04          mov [bp+0x4aa],bx
00002CB3  9A43392802        call 0x228:0x3943
00002CB8  07                pop es
00002CB9  61                popa
00002CBA  EB02              jmp short 0x2cbe
00002CBC  33C0              xor ax,ax
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
00002CF5  F706820A0100      test word [0xa82],0x1
00002CFB  740B              jz 0x2d08
00002CFD  8B0E860A          mov cx,[0xa86]
00002D01  B001              mov al,0x1
00002D03  9A0D842802        call 0x228:0x840d
00002D08  F706820A0800      test word [0xa82],0x8
00002D0E  740B              jz 0x2d1b
00002D10  8B0E8C0A          mov cx,[0xa8c]
00002D14  B004              mov al,0x4
00002D16  9A0D842802        call 0x228:0x840d
00002D1B  C706820A0000      mov word [0xa82],0x0
00002D21  5A                pop dx
00002D22  59                pop cx
00002D23  5B                pop bx
00002D24  C3                ret
00002D25  6A08              push byte +0x8
00002D27  36813EDEFFEAF4    cmp word [ss:0xffde],0xf4ea
00002D2E  F8                clc
00002D2F  750E              jnz 0x2d3f
00002D31  50                push ax
00002D32  36A118FE          mov ax,[ss:0xfe18]
00002D36  360B06DEFD        or ax,[ss:0xfdde]
00002D3B  58                pop ax
00002D3C  7401              jz 0x2d3f
00002D3E  F9                stc
00002D3F  C3                ret
00002D40  6A08              push byte +0x8
00002D42  50                push ax
00002D43  32E4              xor ah,ah
00002D45  8BC8              mov cx,ax
00002D47  49                dec cx
00002D48  B80100            mov ax,0x1
00002D4B  D3E0              shl ax,cl
00002D4D  8BC8              mov cx,ax
00002D4F  58                pop ax
