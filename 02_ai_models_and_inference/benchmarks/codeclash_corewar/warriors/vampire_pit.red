;name Vampire Pit
;author P.Kline & Lauburu Core
;strategy Scans core and traps enemy processes in a fang pit
;assert 1
step    EQU 12
fang    JMP    pit-start, 0
pit     SPL    0, 0
        MOV.I  bomb, <pit
        JMP    pit
bomb    DAT    <1, 1
start   ADD.AB #step, fang
        MOV.I  fang, @fang
        JMP    start
        END start
