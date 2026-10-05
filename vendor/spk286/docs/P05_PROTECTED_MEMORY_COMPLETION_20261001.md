# P05: equivalent protected-memory completion path

The descriptor, event-gate and call-TSS services establish a valid memory
request directly. Their three active states dominate `operand_request` and
`operand_select_rm`, disable register-direct and ordinary access faults,
select offset zero and limit FFFF, and disable expand-down checking.

The generic operand service exposes `unlimited_memory_done`: the completion
predicate after those three preconditions have been established. It retains
reset, semantic cancellation, the blocked state, pending state, check-only
requests and memory-response validity. The CPU selects it only for the three
services. Ordinary operands retain `done`; admission, response readiness,
pending/blocked updates, register writes and all old outputs are unchanged.
No flip-flops, cycles or CPU external ports are added.

`prove_protected_memory_completion.py` restores the changes against commit
`13b467d` and checks the remainder of the CPU top, operand and executor sources.
It uses the actual operand equations and actual CPU instance bindings. Remaining
request/selector terms and the non-service access-fault result are independent
arbitrary booleans, a stronger space than their actual upstream expressions.
Source guards check both access-fault branches and the direct active-state
aliases. The proof includes arbitrary pending/check/response/reset/cancel/
blocked state, both service and ordinary paths, both widths and all ranges.
Removing the blocked-state qualifier is rejected by the negative control.

This is exact two-state combinational equivalence, not a claim about arbitrary
X propagation or historical 80286 cycle accuracy. Directed validation includes
strict `-Wall` CPU lint in base and P01/P02/P05/P06 configurations, operand
service/byte, call-gate/accessed, protected-system, CPU double-fault and task-LDT
banks in Icarus and Verilator. No full CPU regression or hardware run is part
of this milestone. Fresh Quartus results are recorded downstream separately;
the functional proof alone does not establish 50 MHz closure.
