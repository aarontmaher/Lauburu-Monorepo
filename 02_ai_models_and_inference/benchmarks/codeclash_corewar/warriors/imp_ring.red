;name Imp Ring
;author A. K. Dewdney & Lauburu Core
;strategy Imp launcher forming a rotating execution ring
;assert 1
start   SPL    1
        SPL    1
        SPL    1
        MOV.I  imp, @step
step    JMP    start, 2667
imp     MOV.I  0, 1
        END start
