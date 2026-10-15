;name Stone Bomber
;author C. Metcalf & Lauburu Core
;strategy Fast 2-instruction stone bomber
;assert 1
step    EQU 3044
bomb    DAT #step, #1
start   MOV.I  bomb, @ptr
        ADD.F  bomb, ptr
ptr     JMP    start, bomb+step
        END start
