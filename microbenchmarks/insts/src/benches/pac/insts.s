.arch armv8.5-a+memtag
.text

.global pacdzatest
.global pacdzalatencytest
.global pacdatest
.global pacdalatencytest
.global autdzatest
.global autdzalatencytest
.global autdatest
.global autdalatencytest
.global xpacdtest
.global xpacdlatencytest
.global orrlatencytest

// x0: iteration count
pacdzatest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
pacdzatest_loop:
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  mov x13, x15
  pacdza x13
  sub x0, x0, x14
  cbnz x0, pacdzatest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
pacdzalatencytest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
pacdzalatency_loop:
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  pacdza x13
  sub x0, x0, x14
  cbnz x0, pacdzalatency_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
pacdatest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
pacdatest_loop:
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  mov x13, x15
  pacda x13, x14
  sub x0, x0, x14
  cbnz x0, pacdatest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
pacdalatencytest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
pacdalatency_loop:
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  pacda x13, x14
  sub x0, x0, x14
  cbnz x0, pacdalatency_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
autdzatest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  pacdza x15
  mov x14, 20
  eor x13, x13, x13
autdzatest_loop:
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  mov x13, x15
  autdza x13
  sub x0, x0, x14
  cbnz x0, autdzatest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
autdzalatencytest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  pacdza x15
  mov x14, 20
  eor x13, x13, x13
autdzalatencytest_loop:
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  orr x13, x13, x15
  autdza x13
  sub x0, x0, x14
  cbnz x0, autdzalatencytest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
autdatest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  pacda x15, x14
  eor x13, x13, x13
autdatest_loop:
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  mov x13, x15
  autda x13, x14
  sub x0, x0, x14
  cbnz x0, autdatest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret


// x0: iteration count
autdalatencytest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  pacda x15, x14
  eor x13, x13, x13
autdalatencytest_loop:
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  orr x13, x13, x15
  autda x13, x14
  sub x0, x0, x14
  cbnz x0, autdalatencytest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret

// x0: iteration count
xpacdtest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
xpacdtest_loop:
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  mov x13, x15
  xpacd x13
  sub x0, x0, x14
  cbnz x0, xpacdtest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret


// x0: iteration count
xpacdlatencytest:
  sub sp, sp, #0x30
  stp x14, x15, [sp, #0x10]
  stp x12, x13, [sp, #0x20]
  mov x15, 1
  mov x14, 20
  eor x13, x13, x13
xpacdlatencytest_loop:
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  xpacd x13
  sub x0, x0, x14
  cbnz x0, xpacdlatencytest_loop
  ldp x12, x13, [sp, #0x20]
  ldp x14, x15, [sp, #0x10]
  add sp, sp, #0x30
  ret
