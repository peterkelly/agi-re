bits 16

; Called from the planar graphics glyph renderer with its BP frame intact.
; Return AL nonzero when the selected glyph pixel is set. The caller retains
; its existing TEST/branch and pixel-writing code.

    push bx
    push dx
    push es

    xor bx, bx
    mov es, bx
    mov bx, [es:0x010c]       ; INT 43h font offset
    mov dx, [es:0x010e]       ; INT 43h font segment

    mov al, [bp+0x04]         ; character
    mul byte [bp+0x0e]        ; character * active character height
    add bx, ax
    xor ax, ax
    mov al, [bp-0x01]         ; glyph row
    add bx, ax

    mov es, dx
    mov al, [es:bx]
    and al, [bp-0x03]         ; pixel mask

    pop es
    pop dx
    pop bx
    ret
