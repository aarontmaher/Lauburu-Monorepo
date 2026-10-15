;name Lauburu Qwen Champion
;author Lauburu Local AI Mesh
;strategy Adaptive hybrid Paper-Stone warrior with anti-vampire decoys
;assert 1
pStep   EQU 1800
sStep   EQU 3359
start   SPL    paper
stone   MOV.I  sBomb, @sPtr
        ADD.F  sBomb, sPtr
sPtr    JMP    stone, sBomb+sStep
sBomb   DAT    #sStep, #1
paper   SPL    1
        SPL    1
pLoop   SPL    @0, pStep
        MOV.I  }pLoop, >pLoop
        MOV.I  #0, 2667
        JMP    pLoop
        END start
