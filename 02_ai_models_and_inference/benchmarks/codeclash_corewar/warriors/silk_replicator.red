;name Silk Replicator
;author CoreWar Master & Lauburu Core
;strategy Multi-process parallel paper cloner
;assert 1
step1   EQU 2365
step2   EQU 1450
start   SPL    1
        SPL    1
loop    SPL    1
copy1   SPL    @0, step1
        MOV.I  }copy1, >copy1
copy2   SPL    @0, step2
        MOV.I  }copy2, >copy2
        MOV.I  #0, 2667
        JMP    copy1
        END start
