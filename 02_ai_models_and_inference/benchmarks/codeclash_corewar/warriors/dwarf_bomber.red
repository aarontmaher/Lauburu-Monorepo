;name Dwarf Bomber
;author A. K. Dewdney & Lauburu Core
;strategy Classic ICWS'94 Bomber dropping DAT bombs at step 4
;assert 1
step    EQU 4
bomb    DAT #0, #0
start   ADD.AB #step, target
        MOV.I  bomb, @target
        JMP    start
target  DAT #0, #2
        END start
